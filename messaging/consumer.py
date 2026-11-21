import json
import math
import pickle
import sqlite3
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from .message_contract import (
        AI4I_UNITS,
        SENSOR_UNITS,
        SCHEMA_VERSION,
        validate_metadata,
    )
except ImportError:
    from message_contract import (
        AI4I_UNITS,
        SENSOR_UNITS,
        SCHEMA_VERSION,
        validate_metadata,
    )

from detection.train_ai4i_rf import predict_forest
from detection.detection_engine import (
    calculate_z_score, classify_severity, WINDOW, Z_THRESHOLD, ALERT_COOLDOWN
)

try:
    from .mqtt_security import configure_mqtt_auth
except ImportError:
    from mqtt_security import configure_mqtt_auth

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/sensors"
AI4I_TOPIC = "factory/ai4i/replay"

DB_PATH = BASE_DIR / "data" / "sensor_readings.db"
MODEL_PATH = BASE_DIR / "models" / "ai4i_random_forest.pkl"

SENSORS = ["temperature", "vibration", "humidity", "pressure", "current"]

last_alert_time = {}
ai4i_model = None

AI4I_FEATURES = [
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
    "type_L",
    "type_M",
    "type_H",
    "temperature_difference",
    "torque_speed",
]

RECOMMENDATIONS = {
    "temperature": "Inspect cooling system and check for overheating.",
    "vibration": "Inspect rotating equipment, bearings and alignment.",
    "humidity": "Check humidity sensor calibration and moisture levels.",
    "pressure": "Inspect pressure regulator, valves and pipelines.",
    "current": "Inspect electrical connections and motor load.",
}


def ensure_columns(conn, table_name, column_definitions):
    """Add missing metadata columns without recreating or deleting existing data."""
    existing = {
        row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in column_definitions.items():
        if column_name not in existing:
            conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            )


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                temperature REAL,
                vibration REAL,
                humidity REAL,
                pressure REAL,
                current REAL,
                asset_id TEXT DEFAULT 'LEGACY-UNKNOWN',
                source TEXT DEFAULT 'legacy_unknown',
                schema_version TEXT DEFAULT 'legacy',
                event_id TEXT,
                run_id TEXT,
                source_timestamp TEXT,
                units_json TEXT DEFAULT '{}',
                synthetic_fields_json TEXT DEFAULT '[]',
                source_channels_json TEXT DEFAULT '{}',
                actual_anomaly INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                sensor TEXT,
                reading REAL,
                z_score REAL,
                severity TEXT,
                recommendation TEXT,
                asset_id TEXT DEFAULT 'LEGACY-UNKNOWN',
                source TEXT DEFAULT 'legacy_unknown',
                schema_version TEXT DEFAULT 'legacy',
                event_id TEXT,
                run_id TEXT,
                unit TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                udi INTEGER,
                product_id TEXT,
                machine_type TEXT,
                air_temperature REAL,
                process_temperature REAL,
                rotational_speed REAL,
                torque REAL,
                tool_wear REAL,
                failure_score REAL,
                threshold REAL,
                predicted_failure INTEGER,
                actual_failure INTEGER,
                correct INTEGER,
                run_id TEXT,
                asset_id TEXT,
                source TEXT DEFAULT 'legacy_unknown',
                schema_version TEXT DEFAULT 'legacy',
                source_timestamp TEXT,
                event_id TEXT,
                units_json TEXT DEFAULT '{}',
                synthetic_fields_json TEXT DEFAULT '[]',
                source_channels_json TEXT DEFAULT '{}'
            )
        """)

        # Safe additive migration support for older copies of the database.
        ensure_columns(conn, "sensor_readings", {
            "asset_id": "TEXT DEFAULT 'LEGACY-UNKNOWN'",
            "source": "TEXT DEFAULT 'legacy_unknown'",
            "schema_version": "TEXT DEFAULT 'legacy'",
            "event_id": "TEXT",
            "run_id": "TEXT",
            "source_timestamp": "TEXT",
            "units_json": "TEXT DEFAULT '{}'",
            "synthetic_fields_json": "TEXT DEFAULT '[]'",
            "source_channels_json": "TEXT DEFAULT '{}'",
            "actual_anomaly": "INTEGER",
        })
        ensure_columns(conn, "alerts", {
            "asset_id": "TEXT DEFAULT 'LEGACY-UNKNOWN'",
            "source": "TEXT DEFAULT 'legacy_unknown'",
            "schema_version": "TEXT DEFAULT 'legacy'",
            "event_id": "TEXT",
            "run_id": "TEXT",
            "unit": "TEXT",
        })
        ensure_columns(conn, "predictions", {
            "run_id": "TEXT",
            "asset_id": "TEXT",
            "source": "TEXT DEFAULT 'legacy_unknown'",
            "schema_version": "TEXT DEFAULT 'legacy'",
            "source_timestamp": "TEXT",
            "event_id": "TEXT",
            "units_json": "TEXT DEFAULT '{}'",
            "synthetic_fields_json": "TEXT DEFAULT '[]'",
            "source_channels_json": "TEXT DEFAULT '{}'",
        })

        # QoS 1 can redeliver a message. Unique event IDs prevent duplicate rows.
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sensor_readings_event_id_unique
            ON sensor_readings(event_id) WHERE event_id IS NOT NULL
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_event_id_unique
            ON predictions(event_id) WHERE event_id IS NOT NULL
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_readings_asset_source_run
            ON sensor_readings(asset_id, source, run_id, id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_run_id_id
            ON predictions(run_id, id)
        """)


def load_ai4i_model():
    global ai4i_model

    if ai4i_model is not None:
        return ai4i_model
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"AI4I model not found: {MODEL_PATH}")

    with open(MODEL_PATH, "rb") as file:
        model = pickle.load(file)

    if model.get("features") != AI4I_FEATURES:
        raise ValueError("AI4I model feature order does not match the expected features.")
    if not model.get("trees"):
        raise ValueError("AI4I model contains no trees.")

    ai4i_model = model
    print("\nAI4I Random Forest model loaded.")
    print("Number of trees:", len(ai4i_model["trees"]))
    print("Decision threshold:", round(float(ai4i_model["threshold"]), 2))
    return ai4i_model


def check_anomalies(conn, timestamp, readings, current_id, metadata, units_json):
    """Compare only with prior readings from this same asset, source and run."""
    cursor = conn.cursor()

    for sensor in SENSORS:
        if metadata["source"] == "skab_replay" and sensor in metadata["synthetic_fields"]:
            continue
        cursor.execute(f"""
            SELECT {sensor}
            FROM sensor_readings
            WHERE id < ?
              AND asset_id = ?
              AND source = ?
              AND run_id = ?
              AND units_json = ?
              AND source_channels_json = ?
            ORDER BY id DESC
            LIMIT ?
        """, (
            current_id,
            metadata["asset_id"],
            metadata["source"],
            metadata["run_id"],
            units_json,
            json.dumps(metadata["source_channels"], sort_keys=True, separators=(",", ":")),
            WINDOW,
        ))

        previous = [row[0] for row in cursor.fetchall() if row[0] is not None]
        reading = readings[sensor]
        z_score = calculate_z_score(previous, reading)
        if z_score is None:
            continue

        if abs(z_score) <= Z_THRESHOLD:
            continue

        severity = classify_severity(z_score)
        alert_key = (
            metadata["asset_id"], metadata["source"], metadata["run_id"],
            metadata["source_channels"].get("sequence_id"), sensor, severity
        )
        current_time = time.monotonic()
        previous_alert = last_alert_time.get(alert_key)
        if previous_alert is not None and current_time - previous_alert < ALERT_COOLDOWN:
            continue

        recommendation = RECOMMENDATIONS[sensor]
        cursor.execute("""
            INSERT INTO alerts (
                timestamp, sensor, reading, z_score, severity, recommendation,
                asset_id, source, schema_version, event_id, run_id, unit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            sensor,
            reading,
            round(z_score, 2),
            severity,
            recommendation,
            metadata["asset_id"],
            metadata["source"],
            metadata["schema_version"],
            metadata["event_id"],
            metadata["run_id"],
            metadata["units"][sensor],
        ))
        last_alert_time[alert_key] = current_time

        print("\nANOMALY DETECTED!")
        print("Asset:", metadata["asset_id"])
        print("Source:", metadata["source"])
        print("Sensor:", sensor.upper(), "(", metadata["units"][sensor], ")")
        print("Reading:", reading)
        print("Z-score:", round(z_score, 2))
        print("Severity:", severity)
        print("Recommendation:", recommendation)
        print("-" * 50)


def process_sensor_message(data):
    source = validate_metadata(data)
    if source not in SENSOR_UNITS:
        raise ValueError(f"Source '{source}' is not valid for the five-sensor MQTT topic.")

    readings = data.get("readings")
    if not isinstance(readings, dict) or set(readings) != set(SENSORS):
        raise ValueError("Sensor readings must contain exactly the five configured sensor fields.")

    numeric_readings = {}
    for sensor in SENSORS:
        try:
            value = float(readings[sensor])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid numeric value for {sensor}.") from error
        if not math.isfinite(value):
            raise ValueError(f"Non-finite {sensor} reading.")
        numeric_readings[sensor] = value

    actual_anomaly = data.get("actual_anomaly")
    if type(actual_anomaly) is not int or actual_anomaly not in (0, 1):
        raise ValueError("actual_anomaly must be integer 0 or 1.")

    faults = data.get("faults", [])
    if not isinstance(faults, list) or not all(isinstance(item, str) for item in faults):
        raise ValueError("faults must be a list of strings.")

    metadata = data
    units_json = json.dumps(data["units"], sort_keys=True, separators=(",", ":"))
    synthetic_fields_json = json.dumps(data["synthetic_fields"], separators=(",", ":"))
    source_channels_json = json.dumps(data["source_channels"], sort_keys=True, separators=(",", ":"))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO sensor_readings (
                timestamp, temperature, vibration, humidity, pressure, current,
                asset_id, source, schema_version, event_id, run_id,
                source_timestamp, units_json, synthetic_fields_json,
                source_channels_json, actual_anomaly
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["timestamp"],
            numeric_readings["temperature"],
            numeric_readings["vibration"],
            numeric_readings["humidity"],
            numeric_readings["pressure"],
            numeric_readings["current"],
            data["asset_id"],
            source,
            data["schema_version"],
            data["event_id"],
            data["run_id"],
            data["source_timestamp"],
            units_json,
            synthetic_fields_json,
            source_channels_json,
            actual_anomaly,
        ))

        if cursor.rowcount == 0:
            print("Duplicate sensor event ignored:", data["event_id"])
            return

        current_id = cursor.lastrowid
        check_anomalies(
            conn,
            data["timestamp"],
            numeric_readings,
            current_id,
            metadata,
            units_json,
        )

    print(
        "Sensor data saved:", data["timestamp"],
        "| Asset:", data["asset_id"],
        "| Source:", source,
        "| Run:", data["run_id"],
    )


def process_ai4i_message(data):
    source = validate_metadata(data, expected_source="ai4i_replay")
    if source != "ai4i_replay":
        raise ValueError("Invalid source for AI4I replay topic.")

    model = load_ai4i_model()
    readings = data.get("readings")
    expected_fields = set(AI4I_UNITS)
    if not isinstance(readings, dict) or set(readings) != expected_fields:
        raise ValueError("AI4I readings must contain exactly the five required numeric fields.")

    numeric = {}
    for field in AI4I_UNITS:
        try:
            value = float(readings[field])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid numeric AI4I field: {field}") from error
        if not math.isfinite(value):
            raise ValueError(f"Non-finite AI4I field: {field}")
        numeric[field] = value

    udi = data.get("udi")
    actual_failure = data.get("actual_failure")
    machine_type = data.get("machine_type")
    product_id = data.get("product_id")

    if type(udi) is not int or udi <= 0:
        raise ValueError("AI4I UDI must be a positive integer.")
    if type(actual_failure) is not int or actual_failure not in (0, 1):
        raise ValueError("Actual failure label must be integer 0 or 1.")
    if machine_type not in ("L", "M", "H"):
        raise ValueError("Invalid AI4I machine type.")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("AI4I product_id is missing.")

    air = numeric["air_temperature"]
    process = numeric["process_temperature"]
    speed = numeric["rotational_speed"]
    torque = numeric["torque"]
    wear = numeric["tool_wear"]

    features = [
        air,
        process,
        speed,
        torque,
        wear,
        1 if machine_type == "L" else 0,
        1 if machine_type == "M" else 0,
        1 if machine_type == "H" else 0,
        process - air,
        torque * speed / 1000,
    ]

    failure_score = float(predict_forest(model["trees"], [features])[0])
    threshold = round(float(model["threshold"]), 2)
    predicted_failure = 1 if failure_score >= threshold else 0
    correct = int(predicted_failure == actual_failure)

    units_json = json.dumps(data["units"], sort_keys=True, separators=(",", ":"))
    synthetic_fields_json = json.dumps(data["synthetic_fields"], separators=(",", ":"))
    source_channels_json = json.dumps(data["source_channels"], sort_keys=True, separators=(",", ":"))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO predictions (
                timestamp, udi, product_id, machine_type,
                air_temperature, process_temperature, rotational_speed,
                torque, tool_wear, failure_score, threshold,
                predicted_failure, actual_failure, correct,
                run_id, asset_id, source, schema_version, source_timestamp,
                event_id, units_json, synthetic_fields_json, source_channels_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["timestamp"],
            udi,
            product_id,
            machine_type,
            air,
            process,
            speed,
            torque,
            wear,
            round(failure_score, 4),
            threshold,
            predicted_failure,
            actual_failure,
            correct,
            data["run_id"],
            data["asset_id"],
            source,
            data["schema_version"],
            data["source_timestamp"],
            data["event_id"],
            units_json,
            synthetic_fields_json,
            source_channels_json,
        ))

        if cursor.rowcount == 0:
            print("Duplicate AI4I event ignored:", data["event_id"])
            return

    print("\nAI4I MACHINE PREDICTION")
    print("Run ID:", data["run_id"])
    print("Event ID:", data["event_id"])
    print("UDI:", udi)
    print("Product ID:", product_id)
    print("Machine type:", machine_type)
    print("Failure score:", round(failure_score * 100, 2), "%")
    print("Decision threshold:", round(threshold * 100, 2), "%")
    print("Predicted:", "FAILURE" if predicted_failure else "NORMAL")
    print("Actual:", "FAILURE" if actual_failure else "NORMAL")
    print("Prediction:", "CORRECT" if correct else "INCORRECT")
    print("-" * 50)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT Broker!")
        client.subscribe([(TOPIC, 1), (AI4I_TOPIC, 1)])
        print("Subscribed to topics:")
        print("-", TOPIC)
        print("-", AI4I_TOPIC, "\n")
    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == TOPIC:
            process_sensor_message(data)
        elif msg.topic == AI4I_TOPIC:
            process_ai4i_message(data)
        else:
            print("Unknown MQTT topic:", msg.topic)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        print(f"Rejected invalid message from {msg.topic}: {error}")
    except Exception as error:
        print(f"Unexpected error processing message from {msg.topic}: {error}")



def main():
    create_database()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print("MQTT Consumer Started")
    print("Automatic Anomaly Detection Enabled")
    print("Z-score threshold:", Z_THRESHOLD)
    print("Alert cooldown:", ALERT_COOLDOWN, "seconds")
    print("AI4I Random Forest prediction processing enabled")
    print("Message schema version:", SCHEMA_VERSION)
    print("Waiting for sensor and AI4I replay data...\n")

    try:
        configure_mqtt_auth(client, "consumer")
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nConsumer stopped.")
    except Exception as error:
        print("Error:", error)
    finally:
        client.disconnect()


if __name__ == '__main__':
    main()
