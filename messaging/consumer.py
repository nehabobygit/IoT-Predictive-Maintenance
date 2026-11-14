
import json
import sqlite3
import statistics
import time
import paho.mqtt.client as mqtt
from pathlib import Path

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/sensors"

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sensor_readings.db"

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

RECOMMENDATIONS = {
    "temperature": "Inspect cooling system and check for overheating.",
    "vibration": "Inspect rotating equipment, bearings and alignment.",
    "humidity": "Check humidity sensor calibration and moisture levels.",
    "pressure": "Inspect pressure regulator, valves and pipelines.",
    "current": "Inspect electrical connections and motor load."
}


def create_database():
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


def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(TOPIC)
        print("Subscribed to topic:", TOPIC, "\n")
    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):

    try:
        data = json.loads(msg.payload.decode())

        timestamp = data["timestamp"]
        readings = data["readings"]

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

        print("Data saved:", timestamp)

    except Exception as e:
        print("Error processing message:", e)


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
print("Separate cooldowns for each sensor and severity")
print("Waiting for sensor data...\n")

try:
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

except KeyboardInterrupt:
    print("\nConsumer stopped.")

except Exception as e:
    print("Error:", e)

finally:
    client.disconnect()
