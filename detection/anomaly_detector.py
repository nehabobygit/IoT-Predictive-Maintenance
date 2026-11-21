
import sqlite3
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sensor_readings.db"

SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current"
]

WINDOW = 10
Z_THRESHOLD = 1.5


def classify_severity(z_score):

    score = abs(z_score)

    if score >= 5:
        return "HIGH"
    elif score >= 3.5:
        return "MEDIUM"
    else:
        return "LOW"


def get_recommendation(sensor):

    recommendations = {
        "temperature": "Inspect cooling system and check for overheating.",
        "vibration": "Inspect rotating equipment, bearings and alignment.",
        "humidity": "Check humidity sensor calibration and moisture levels.",
        "pressure": "Inspect pressure regulator, valves and pipelines.",
        "current": "Inspect electrical connections and motor load."
    }

    return recommendations[sensor]


def detect_anomalies():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
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

    conn.commit()

    cursor.execute("""
        SELECT timestamp, temperature, vibration,
               humidity, pressure, current
        FROM sensor_readings
        ORDER BY id
    """)

    rows = cursor.fetchall()

    if len(rows) < 6:
        print("Not enough readings to detect anomalies.")
        conn.close()
        return

    print("\nPREDICTIVE MAINTENANCE ALERT SYSTEM")
    print("=" * 65)

    total_anomalies = 0

    for column, sensor in enumerate(SENSORS, start=1):

        values = [row[column] for row in rows]

        for i in range(5, len(values)):

            previous = values[max(0, i - WINDOW):i]

            mean = statistics.mean(previous)
            std = statistics.stdev(previous)

            if std == 0:
                continue

            z_score = (values[i] - mean) / std

            if abs(z_score) > Z_THRESHOLD:

                severity = classify_severity(z_score)
                recommendation = get_recommendation(sensor)

                cursor.execute("""
                    INSERT INTO alerts
                    (timestamp, sensor, reading, z_score,
                     severity, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rows[i][0],
                    sensor,
                    values[i],
                    round(z_score, 2),
                    severity,
                    recommendation
                ))

                conn.commit()

                print("\nALERT:", severity)
                print("Sensor:", sensor.upper())
                print("Reading:", values[i])
                print("Timestamp:", rows[i][0])
                print("Z-score:", round(z_score, 2))
                print("Maintenance Recommendation:", recommendation)

                total_anomalies += 1

    print("\n" + "=" * 65)
    print("TOTAL ANOMALIES:", total_anomalies)
    print("Alerts saved to database:", total_anomalies)
    print("=" * 65)

    conn.close()


if __name__ == "__main__":
    detect_anomalies()
