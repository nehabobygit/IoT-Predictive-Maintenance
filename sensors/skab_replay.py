
import csv
import json
import random
import time
from pathlib import Path

import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "localhost"
PORT = 1883
TOPIC = "factory/sensors"

# SKAB dataset folder
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"

def replay():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("SKAB Dataset Replay Started")
        print("Publishing real industrial sensor readings...\n")

        files = sorted(
            DATA_FOLDER.glob("*.csv"),
            key=lambda path: int(path.stem)
        )

        for file_path in files:
            print("Replaying:", file_path.name)

            with open(file_path, newline="") as file:
                reader = csv.DictReader(file, delimiter=";")

                for row in reader:
                    readings = {
                        "temperature": float(row["Temperature"]),
                        "vibration": float(row["Accelerometer1RMS"]),
                        "humidity": round(random.uniform(30, 70), 2),
                        "pressure": float(row["Pressure"]),
                        "current": float(row["Current"])
                    }

                    data = {
                        "timestamp": row["datetime"],
                        "readings": readings,
                        "faults": [],
                        "actual_anomaly": int(float(row["anomaly"]))
                    }

                    client.publish(TOPIC, json.dumps(data))

                    print(
                        "Published:",
                        data["timestamp"],
                        "| Actual anomaly:",
                        data["actual_anomaly"]
                    )

                    time.sleep(0.05)

        print("\nSKAB dataset replay completed!")

    except KeyboardInterrupt:
        print("\nReplay stopped by user.")

    except Exception as error:
        print("Error:", error)

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    replay()
