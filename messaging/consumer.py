
import json
import sqlite3
import statistics
import time
import math
import sys
import pickle

import paho.mqtt.client as mqtt
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

BROKER = "localhost"
PORT = 1883

TOPIC = "factory/sensors"
AI4I_TOPIC = "factory/ai4i/replay"

DB_PATH = BASE_DIR / "data" / "sensor_readings.db"
MODEL_PATH = BASE_DIR / "models" / "ai4i_random_forest.pkl"

# Make the project root available for importing the existing model function.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from detection.train_ai4i_rf import predict_forest


SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current"
]

WINDOW = 10
Z_THRESHOLD = 1.5
ALERT_COOLDOWN = 30

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
    "torque_speed"
]

RECOMMENDATIONS = {
    "temperature": "Inspect cooling system and check for overheating.",
    "vibration": "Inspect rotating equipment, bearings and alignment.",
    "humidity": "Check humidity sensor calibration and moisture levels.",
    "pressure": "Inspect pressure regulator, valves and pipelines.",
    "current": "Inspect electrical connections and motor load."
}


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
                current REAL
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
                recommendation TEXT
            )
        """)

        # Separate table for AI4I machine-failure predictions.
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
                correct INTEGER
            )
        """)


def load_ai4i_model():

    global ai4i_model

    if ai4i_model is not None:
        return ai4i_model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"AI4I model not found: {MODEL_PATH}"
        )

    with open(MODEL_PATH, "rb") as file:
        model = pickle.load(file)

    if model.get("features") != AI4I_FEATURES:
        raise ValueError(
            "AI4I model feature order does not match the expected features."
        )

    if not model.get("trees"):
        raise ValueError("AI4I model contains no trees.")

    ai4i_model = model

    print("\nAI4I Random Forest model loaded.")
    print("Number of trees:", len(ai4i_model["trees"]))
    print("Decision threshold:", ai4i_model["threshold"])

    return ai4i_model


def classify_severity(z_score):

    score = abs(z_score)

    if score >= 5:
        return "HIGH"
    elif score >= 3.5:
        return "MEDIUM"
    else:
        return "LOW"


def check_anomalies(conn, timestamp, readings, current_id):

    cursor = conn.cursor()

    for sensor in SENSORS:

        cursor.execute(f"""
            SELECT {sensor}
            FROM sensor_readings
            WHERE id < ?
            ORDER BY id DESC
            LIMIT ?
        """, (current_id, WINDOW))

        previous = [row[0] for row in cursor.fetchall()]

        if len(previous) < 5:
            continue

        mean = statistics.mean(previous)
        std = statistics.stdev(previous)

        if std == 0:
            continue

        reading = readings[sensor]
        z_score = (reading - mean) / std

        if abs(z_score) > Z_THRESHOLD:

            severity = classify_severity(z_score)

            current_time = time.monotonic()

            # Separate cooldown for each sensor and severity.
            alert_key = (sensor, severity)
            previous_alert = last_alert_time.get(alert_key, 0)

            if current_time - previous_alert < ALERT_COOLDOWN:
                continue

            recommendation = RECOMMENDATIONS[sensor]

            cursor.execute("""
                INSERT INTO alerts
                (timestamp, sensor, reading, z_score,
                 severity, recommendation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                sensor,
                reading,
                round(z_score, 2),
                severity,
                recommendation
            ))

            last_alert_time[alert_key] = current_time

            print("\nANOMALY DETECTED!")
            print("Sensor:", sensor.upper())
            print("Reading:", reading)
            print("Z-score:", round(z_score, 2))
            print("Severity:", severity)
            print("Recommendation:", recommendation)
            print("-" * 50)


def process_sensor_message(data):

    timestamp = data["timestamp"]
    readings = data["readings"]

    for sensor in SENSORS:
        value = float(readings[sensor])

        if not math.isfinite(value):
            raise ValueError(f"Invalid {sensor} reading.")

        readings[sensor] = value

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sensor_readings
            (timestamp, temperature, vibration, humidity, pressure, current)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            readings["temperature"],
            readings["vibration"],
            readings["humidity"],
            readings["pressure"],
            readings["current"]
        ))

        current_id = cursor.lastrowid

        check_anomalies(
            conn, timestamp, readings, current_id
        )

    print("Sensor data saved:", timestamp)


def process_ai4i_message(data):

    model = load_ai4i_model()

    timestamp = data["timestamp"]
    udi = int(data["udi"])
    product_id = str(data["product_id"])
    machine_type = data["machine_type"]

    if machine_type not in ("L", "M", "H"):
        raise ValueError("Invalid AI4I machine type.")

    readings = data["readings"]

    air = float(readings["air_temperature"])
    process = float(readings["process_temperature"])
    speed = float(readings["rotational_speed"])
    torque = float(readings["torque"])
    wear = float(readings["tool_wear"])

    values = [air, process, speed, torque, wear]

    if not all(math.isfinite(value) for value in values):
        raise ValueError("AI4I message contains invalid numeric values.")

    actual_failure = int(data["actual_failure"])

    if actual_failure not in (0, 1):
        raise ValueError("Actual failure label must be 0 or 1.")

    type_l = 1 if machine_type == "L" else 0
    type_m = 1 if machine_type == "M" else 0
    type_h = 1 if machine_type == "H" else 0

    # Keep the exact feature order used during model training.
    features = [
        air,
        process,
        speed,
        torque,
        wear,
        type_l,
        type_m,
        type_h,
        process - air,
        torque * speed / 1000
    ]

    failure_score = float(
        predict_forest(model["trees"], [features])[0]
    )

    threshold = round(float(model["threshold"]), 2)

    predicted_failure = (
        1 if failure_score >= threshold else 0
    )

    correct = int(predicted_failure == actual_failure)

    with sqlite3.connect(DB_PATH) as conn:

        conn.execute("""
            INSERT INTO predictions (
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
                correct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
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
            correct
        ))

    print("\nAI4I MACHINE PREDICTION")
    print("UDI:", udi)
    print("Product ID:", product_id)
    print("Machine type:", machine_type)
    print("Failure score:", round(failure_score * 100, 2), "%")
    print("Decision threshold:", round(threshold * 100, 2), "%")
    print(
        "Predicted:",
        "FAILURE" if predicted_failure else "NORMAL"
    )
    print(
        "Actual:",
        "FAILURE" if actual_failure else "NORMAL"
    )
    print("Prediction:", "CORRECT" if correct else "INCORRECT")
    print("-" * 50)


def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:

        print("Connected to MQTT Broker!")

        client.subscribe([
            (TOPIC, 0),
            (AI4I_TOPIC, 0)
        ])

        print("Subscribed to topics:")
        print("-", TOPIC)
        print("-", AI4I_TOPIC, "\n")

    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):

    try:

        data = json.loads(msg.payload.decode())

        if msg.topic == TOPIC:

            process_sensor_message(data)

        elif msg.topic == AI4I_TOPIC:

            process_ai4i_message(data)

        else:
            print("Unknown MQTT topic:", msg.topic)

    except Exception as error:

        print(
            f"Error processing message from {msg.topic}:",
            error
        )


create_database()

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message

print("MQTT Consumer Started")
print("Automatic Anomaly Detection Enabled")
print("Z-score threshold:", Z_THRESHOLD)
print("Alert cooldown:", ALERT_COOLDOWN, "seconds")
print("AI4I Random Forest prediction processing enabled")
print("Waiting for sensor and AI4I replay data...\n")


try:

    client.connect(BROKER, PORT, 60)
    client.loop_forever()

except KeyboardInterrupt:

    print("\nConsumer stopped.")

except Exception as error:

    print("Error:", error)

finally:

    client.disconnect()
