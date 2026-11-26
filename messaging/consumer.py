from contextlib import closing

import json
import math
import os
import queue
import threading
import urllib.error
import urllib.request
import sqlite3
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from messaging.model_security import load_verified_ai4i_model

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
from detection.train_ai4i_improved import FEATURES, LEGACY_FEATURES, operating_features, physical_features
from detection.live_maintenance import forecast
from detection.detection_engine import (
    calculate_z_score,
    classify_severity,
    WINDOW,
    Z_THRESHOLD,
    ALERT_COOLDOWN,
)
from detection.hybrid_detector import detect_anomalies

try:
    from .mqtt_security import connect_configured
except ImportError:
    from mqtt_security import connect_configured


BROKER = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "8883"))
TOPIC = "factory/sensors"
AI4I_TOPIC = "factory/ai4i/replay"

DB_PATH = Path(os.getenv("IOT_DB_PATH", BASE_DIR / "data" / "sensor_readings.db")).resolve()
MODEL_PATH = Path(os.getenv("AI4I_MODEL_PATH", BASE_DIR / "models" / "ai4i_improved.pkl"))

SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current",
]

last_alert_time = {}
ai4i_model = None
READY = Path(os.getenv("MQTT_CONSUMER_READY_FILE", "/tmp/iot-consumer-ready")) if os.getenv("DOCKER_ENV") == "1" else None

# Optional external HIGH-severity alerts. No webhook means no network calls.
WEBHOOK_URL = os.environ.get("MAINTENANCE_WEBHOOK_URL", "").strip()
WEBHOOK_TOKEN = os.environ.get("MAINTENANCE_WEBHOOK_TOKEN", "").strip()
notification_queue = queue.Queue(maxsize=200)


def notification_worker():
    """Send notifications outside the MQTT callback to avoid blocking ingestion."""
    while True:
        payload = notification_queue.get()
        try:
            body = json.dumps({
                "content": (
                    f"🚨 HIGH-SEVERITY MAINTENANCE ALERT\n"
                    f"Machine: {payload['asset_id']}\n"
                    f"Sensor: {payload['sensor'].upper()}\n"
                    f"Reading: {payload['reading']} {payload['unit']}\n"
                    f"Severity: {payload['severity']}\n"
                    f"Recommendation: {payload['recommendation']}"
                    )
}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if WEBHOOK_TOKEN:
                headers["Authorization"] = f"Bearer {WEBHOOK_TOKEN}"
            request = urllib.request.Request(
                WEBHOOK_URL, data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"Webhook returned HTTP {response.status}")
            print("Webhook notification delivered:", payload["event_id"])
        except Exception as error:
            print("Webhook notification failed:", error)
        finally:
            notification_queue.task_done()


def notify_committed_high_alerts(event_id):
    """Queue only committed HIGH alerts for this event; never block MQTT."""
    if not WEBHOOK_URL:
        return
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        rows = conn.execute("""
            SELECT timestamp, asset_id, sensor, reading, unit,
                   severity, recommendation, event_id, run_id, source
            FROM alerts WHERE event_id = ? AND severity = 'HIGH'
        """, (event_id,)).fetchall()
    fields = (
        "timestamp", "asset_id", "sensor", "reading", "unit",
        "severity", "recommendation", "event_id", "run_id", "source"
    )
    for row in rows:
        try:
            notification_queue.put_nowait(dict(zip(fields, row)))
        except queue.Full:
            print("Webhook queue full; alert remains saved in SQLite:", event_id)


AI4I_FEATURES = LEGACY_FEATURES

RECOMMENDATIONS = {
    "maintenance": "Schedule an inspection of bearings, cooling and motor load.",
    "temperature": "Inspect cooling system and check for overheating.",
    "vibration": "Inspect rotating equipment, bearings and alignment.",
    "humidity": "Check humidity sensor calibration and moisture levels.",
    "pressure": "Inspect pressure regulator, valves and pipelines.",
    "current": "Inspect electrical connections and motor load.",
}


def ensure_columns(conn, table_name, column_definitions):
    """Add missing metadata columns without deleting existing data."""
    existing = {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    for column_name, definition in column_definitions.items():
        if column_name not in existing:
            conn.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {definition}"
            )


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("BEGIN IMMEDIATE")
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_events (
                reading_id INTEGER NOT NULL REFERENCES sensor_readings(id),
                sensor TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                explanation TEXT NOT NULL,
                PRIMARY KEY (reading_id, sensor)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_forecasts (
                reading_id INTEGER PRIMARY KEY REFERENCES sensor_readings(id),
                score REAL NOT NULL,
                threshold REAL NOT NULL,
                horizon_seconds INTEGER NOT NULL
            )
        """)
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
            "category": "TEXT",
            "explanation": "TEXT",
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

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_asset_id
            ON sensor_readings(asset_id, id DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_event_id ON alerts(event_id)
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_sensor_readings_event_id_unique
            ON sensor_readings(event_id)
            WHERE event_id IS NOT NULL
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_predictions_event_id_unique
            ON predictions(event_id)
            WHERE event_id IS NOT NULL
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_sensor_readings_asset_source_run
            ON sensor_readings(asset_id, source, run_id, id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_predictions_run_id_id
            ON predictions(run_id, id)
        """)


def load_ai4i_model():
    global ai4i_model

    if ai4i_model is not None:
        return ai4i_model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"AI4I model not found: {MODEL_PATH}"
        )

    model = load_verified_ai4i_model(MODEL_PATH, BASE_DIR / "models")

    if model.get("features") not in (FEATURES, LEGACY_FEATURES):
        raise ValueError(
            "AI4I model feature order does not match "
            "the expected features."
        )

    if not model.get("trees"):
        raise ValueError(
            "AI4I model contains no trees."
        )

    ai4i_model = model

    print("\nAI4I model loaded:", model["model_type"])
    print("Number of trees:", len(ai4i_model["trees"]))
    print(
        "Decision threshold:",
        round(float(ai4i_model["threshold"]), 2),
    )

    return ai4i_model


def get_sensor_history(cursor, current_id, metadata, units_json):
    """Return a chronological window for the same asset and acquisition stream."""
    cursor.execute("""
        SELECT temperature, vibration, humidity, pressure, current
        FROM sensor_readings
        WHERE id < ? AND asset_id = ? AND source = ? AND run_id = ?
          AND units_json = ? AND source_channels_json = ?
        ORDER BY id DESC LIMIT ?
    """, (
        current_id, metadata["asset_id"], metadata["source"], metadata["run_id"],
        units_json, json.dumps(metadata["source_channels"], sort_keys=True, separators=(",", ":")),
        WINDOW,
    ))
    return list(reversed(cursor.fetchall()))


def score_ai4i(model, features):
    rows = physical_features([features]) if model.get("features") == FEATURES else [features]
    return float(predict_forest(model["trees"], rows)[0]), float(model["threshold"])


def save_alert(
    cursor,
    timestamp,
    sensor,
    reading,
    z_score,
    severity,
    metadata,
    category,
    explanation,
    pending_alerts,
):
    """
    Preserve existing alert storage and cooldown behaviour.
    """
    alert_key = (
        metadata["asset_id"],
        metadata["source"],
        metadata["run_id"],
        metadata["source_channels"].get("sequence_id"),
        sensor,
        severity,
    )

    current_time = time.monotonic()
    previous_alert = last_alert_time.get(alert_key)

    if (
        previous_alert is not None
        and current_time - previous_alert < ALERT_COOLDOWN
    ):
        return False

    cursor.execute("""
        INSERT INTO alerts (
            timestamp,
            sensor,
            reading,
            z_score,
            severity,
            recommendation,
            asset_id,
            source,
            schema_version,
            event_id,
            run_id,
            unit, category, explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        sensor,
        reading,
        round(z_score, 2),
        severity,
        RECOMMENDATIONS[sensor],
        metadata["asset_id"],
        metadata["source"],
        metadata["schema_version"],
        metadata["event_id"],
        metadata["run_id"],
        metadata["units"].get(sensor, "%"), category, explanation,
    ))

    pending_alerts[alert_key] = current_time

    return True


def check_anomalies(conn, timestamp, readings, current_id, metadata, units_json):
    cursor = conn.cursor()
    pending_alerts = {}
    rows = get_sensor_history(cursor, current_id, metadata, units_json)
    history = {sensor: [row[index] for row in rows if row[index] is not None]
               for index, sensor in enumerate(SENSORS)}
    simulator = metadata["source"] == "simulated_sensor"

    def record(sensor, severity, category, explanation, z_score, reading):
        cursor.execute(
            "INSERT INTO anomaly_events VALUES (?, ?, ?, ?, ?)",
            (current_id, sensor, category, severity, explanation),
        )
        save_alert(cursor, timestamp, sensor, reading, z_score, severity,
                   metadata, category, explanation, pending_alerts)

    if simulator:
        findings = detect_anomalies(history, readings)
        for sensor, finding in findings.items():
            reading = readings[sensor]
            severe = (sensor == "temperature" and reading >= 60
                      or sensor == "vibration" and reading >= 14
                      or sensor == "pressure" and reading <= 1
                      or sensor == "current" and reading >= 28)
            z_score = calculate_z_score(history[sensor], reading) or 0.0
            severity = "HIGH" if severe else "MEDIUM" if len(findings) > 1 or finding.score >= 4 else "LOW"
            record(sensor, severity, finding.category, finding.explanation, z_score, reading)

        result = forecast((rows + [tuple(readings[sensor] for sensor in SENSORS)])[-WINDOW:])
        if result is not None:
            score, threshold, seconds = result
            cursor.execute("INSERT INTO maintenance_forecasts VALUES (?, ?, ?, ?)",
                           (current_id, score, threshold, seconds))
            if score >= threshold:
                explanation = f"Recent sensor levels and trends indicate degradation risk within {seconds} seconds."
                save_alert(cursor, timestamp, "maintenance", round(score * 100, 2), 0.0,
                           "HIGH", metadata, "degradation_forecast", explanation, pending_alerts)
        return pending_alerts

    for sensor in SENSORS:
        if metadata["source"] == "skab_replay" and sensor in metadata["synthetic_fields"]:
            continue
        score = calculate_z_score(history[sensor], readings[sensor])
        if score is not None and abs(score) > Z_THRESHOLD:
            record(sensor, classify_severity(score), "statistical_deviation",
                   f"Reading is {abs(score):.1f} standard deviations from its recent mean.",
                   score, readings[sensor])
    return pending_alerts


def process_sensor_message(data):
    source = validate_metadata(data)

    if source not in SENSOR_UNITS:
        raise ValueError(
            f"Source '{source}' is not valid "
            "for the five-sensor MQTT topic."
        )

    readings = data.get("readings")

    if (
        not isinstance(readings, dict)
        or set(readings) != set(SENSORS)
    ):
        raise ValueError(
            "Sensor readings must contain exactly "
            "the five configured sensor fields."
        )

    numeric_readings = {}

    for sensor in SENSORS:
        try:
            value = float(readings[sensor])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid numeric value for {sensor}."
            ) from error

        if isinstance(readings[sensor], bool) or not math.isfinite(value):
            raise ValueError(
                f"Invalid finite numeric {sensor} reading."
            )

        if (source == "simulated_sensor" and
            (sensor == "humidity" and not 0 <= value <= 100
             or sensor in {"vibration", "pressure", "current"} and value < 0)):
            raise ValueError(f"Out-of-range {sensor} reading.")
        numeric_readings[sensor] = value

    actual_anomaly = data.get("actual_anomaly")

    if (
        type(actual_anomaly) is not int
        or actual_anomaly not in (0, 1)
    ):
        raise ValueError(
            "actual_anomaly must be integer 0 or 1."
        )

    faults = data.get("faults", [])

    if (
        not isinstance(faults, list)
        or not all(isinstance(item, str) for item in faults)
    ):
        raise ValueError(
            "faults must be a list of strings."
        )

    metadata = data

    units_json = json.dumps(
        data["units"],
        sort_keys=True,
        separators=(",", ":"),
    )

    synthetic_fields_json = json.dumps(
        data["synthetic_fields"],
        separators=(",", ":"),
    )

    source_channels_json = json.dumps(
        data["source_channels"],
        sort_keys=True,
        separators=(",", ":"),
    )

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO sensor_readings (
                timestamp,
                temperature,
                vibration,
                humidity,
                pressure,
                current,
                asset_id,
                source,
                schema_version,
                event_id,
                run_id,
                source_timestamp,
                units_json,
                synthetic_fields_json,
                source_channels_json,
                actual_anomaly
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
            print(
                "Duplicate sensor event ignored:",
                data["event_id"],
            )
            return

        current_id = cursor.lastrowid

        pending_alerts = check_anomalies(
            conn,
            data["timestamp"],
            numeric_readings,
            current_id,
            metadata,
            units_json,
        )

    # Advance the alert cooldown only after SQLite commits the event and alerts.
    if pending_alerts:
        oldest = time.monotonic() - ALERT_COOLDOWN
        for key, sent_at in list(last_alert_time.items()):
            if sent_at <= oldest:
                del last_alert_time[key]
        last_alert_time.update(pending_alerts)
    notify_committed_high_alerts(data["event_id"])

    print(
        "Sensor data saved:",
        data["timestamp"],
        "| Asset:",
        data["asset_id"],
        "| Source:",
        source,
        "| Run:",
        data["run_id"],
    )


def process_ai4i_message(data):
    source = validate_metadata(
        data,
        expected_source="ai4i_replay",
    )

    if source != "ai4i_replay":
        raise ValueError(
            "Invalid source for AI4I replay topic."
        )

    model = load_ai4i_model()
    readings = data.get("readings")
    expected_fields = set(AI4I_UNITS)

    if (
        not isinstance(readings, dict)
        or set(readings) != expected_fields
    ):
        raise ValueError(
            "AI4I readings must contain exactly "
            "the five required numeric fields."
        )

    numeric = {}

    for field in AI4I_UNITS:
        try:
            value = float(readings[field])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid numeric AI4I field: {field}"
            ) from error

        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite AI4I field: {field}"
            )

        numeric[field] = value

    udi = data.get("udi")
    actual_failure = data.get("actual_failure")
    machine_type = data.get("machine_type")
    product_id = data.get("product_id")

    if type(udi) is not int or udi <= 0:
        raise ValueError(
            "AI4I UDI must be a positive integer."
        )

    if (
        type(actual_failure) is not int
        or actual_failure not in (0, 1)
    ):
        raise ValueError(
            "Actual failure label must be integer 0 or 1."
        )

    if machine_type not in ("L", "M", "H"):
        raise ValueError(
            "Invalid AI4I machine type."
        )

    if (
        not isinstance(product_id, str)
        or not product_id.strip()
    ):
        raise ValueError(
            "AI4I product_id is missing."
        )

    air = numeric["air_temperature"]
    process = numeric["process_temperature"]
    speed = numeric["rotational_speed"]
    torque = numeric["torque"]
    wear = numeric["tool_wear"]

    features = operating_features(air, process, speed, torque, wear, machine_type)
    failure_score, threshold = score_ai4i(model, features)

    predicted_failure = (
        1 if failure_score >= threshold else 0
    )

    correct = int(
        predicted_failure == actual_failure
    )

    units_json = json.dumps(
        data["units"],
        sort_keys=True,
        separators=(",", ":"),
    )

    synthetic_fields_json = json.dumps(
        data["synthetic_fields"],
        separators=(",", ":"),
    )

    source_channels_json = json.dumps(
        data["source_channels"],
        sort_keys=True,
        separators=(",", ":"),
    )

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO predictions (
                timestamp,
                udi,
                product_id,
                machine_type,
                air_temperature,
                process_temperature,
                rotational_speed,
                torque,
                tool_wear,
                failure_score,
                threshold,
                predicted_failure,
                actual_failure,
                correct,
                run_id,
                asset_id,
                source,
                schema_version,
                source_timestamp,
                event_id,
                units_json,
                synthetic_fields_json,
                source_channels_json
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
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
            print(
                "Duplicate AI4I event ignored:",
                data["event_id"],
            )
            return

    print("\nAI4I MACHINE PREDICTION")
    print("Run ID:", data["run_id"])
    print("Event ID:", data["event_id"])
    print("UDI:", udi)
    print("Product ID:", product_id)
    print("Machine type:", machine_type)
    print(
        "Failure score:",
        round(failure_score * 100, 2),
        "%",
    )
    print(
        "Decision threshold:",
        round(threshold * 100, 2),
        "%",
    )
    print(
        "Predicted:",
        "FAILURE" if predicted_failure else "NORMAL",
    )
    print(
        "Actual:",
        "FAILURE" if actual_failure else "NORMAL",
    )
    print(
        "Prediction:",
        "CORRECT" if correct else "INCORRECT",
    )
    print("-" * 50)


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):
    if reason_code == 0:
        print("Connected to MQTT Broker!")

        client.subscribe([
            (TOPIC, 1),
            (AI4I_TOPIC, 1),
        ])

        print("Subscribed to topics:")
        print("-", TOPIC)
        print("-", AI4I_TOPIC, "\n")
    else:
        print(
            "Connection failed:",
            reason_code,
        )


def on_subscribe(client, userdata, mid, reason_codes, properties):
    if any(code.is_failure for code in reason_codes):
        raise RuntimeError("The broker refused the consumer subscriptions.")
    if READY:
        READY.touch()


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if READY:
        READY.unlink(missing_ok=True)


def on_message(client, userdata, msg):
    try:
        data = json.loads(
            msg.payload.decode("utf-8")
        )

        if msg.topic == TOPIC:
            process_sensor_message(data)

        elif msg.topic == AI4I_TOPIC:
            process_ai4i_message(data)

        else:
            print(
                "Unknown MQTT topic:",
                msg.topic,
            )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        print(
            f"Rejected invalid message "
            f"from {msg.topic}: {error}"
        )

    if msg.qos:
        client.ack(msg.mid, msg.qos)


def main():
    create_database()

    if WEBHOOK_URL:
        if not WEBHOOK_URL.startswith("https://"):
            raise ValueError("MAINTENANCE_WEBHOOK_URL must use HTTPS.")
        threading.Thread(target=notification_worker, daemon=True).start()
        print("HIGH-severity webhook notifications enabled")
    else:
        print("Webhook notifications disabled (no URL configured)")

    if READY:
        READY.unlink(missing_ok=True)
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=os.getenv("MQTT_CONSUMER_CLIENT_ID", "iot-maintenance-consumer"),
        clean_session=False,
        manual_ack=True,
    )

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect

    print("MQTT Consumer Started")
    print("Hybrid Anomaly Detection Enabled")
    print("Original Z-score Detection Enabled for SKAB")
    print("Z-score threshold:", Z_THRESHOLD)
    print(
        "Alert cooldown:",
        ALERT_COOLDOWN,
        "seconds",
    )
    print(
        "AI4I Random Forest prediction "
        "processing enabled"
    )
    print(
        "Message schema version:",
        SCHEMA_VERSION,
    )
    print(
        "Waiting for sensor and AI4I replay data...\n"
    )

    try:
        connect_configured(client, "consumer", asynchronous=True)
        client.loop_forever(retry_first_connection=True)

    except KeyboardInterrupt:
        print("\nConsumer stopped.")

    except Exception as error:
        raise RuntimeError("MQTT consumer stopped unexpectedly") from error

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
