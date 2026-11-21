import csv
import json
import random
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from messaging.message_contract import SENSOR_UNITS, build_metadata, new_id

from messaging.mqtt_security import configure_mqtt_auth

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/sensors"

DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"

ASSET_ID = "SKAB-VALVE1"
SOURCE = "skab_replay"

SOURCE_CHANNELS = {
    "temperature": "Temperature",
    "vibration": "Accelerometer1RMS",
    "humidity": "synthetic_random_uniform_30_70",
    "pressure": "Pressure",
    "current": "Current",
    "additional_available_channels": [
        "Accelerometer2RMS",
        "Thermocouple",
        "Voltage",
        "Volume Flow RateRMS",
        "changepoint",
    ],
    "anomaly_label": "anomaly",
}

SYNTHETIC_FIELDS = ["humidity"]


def replay():

    run_id = new_id()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    try:

        if not DATA_FOLDER.exists():
            raise FileNotFoundError(
                f"SKAB dataset folder not found: {DATA_FOLDER}"
            )

        files = sorted(
            DATA_FOLDER.glob("*.csv"),
            key=lambda path: int(path.stem)
        )

        if not files:
            raise FileNotFoundError(
                f"No SKAB CSV files found in: {DATA_FOLDER}"
            )

        configure_mqtt_auth(client, "publisher")

        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("SKAB Dataset Replay Started")
        print("MQTT topic:", TOPIC)
        print("Asset ID:", ASSET_ID)
        print("Source:", SOURCE)
        print("Run ID:", run_id)
        print("Humidity is synthetic; vibration is measured in g.\n")

        published = 0

        for file_path in files:

            sequence_id = new_id()

            print("\nReplaying:", file_path.name)
            print("Sequence ID:", sequence_id)

            with open(
                file_path,
                newline="",
                encoding="utf-8-sig"
            ) as file:

                reader = csv.DictReader(file, delimiter=";")

                required_columns = {
                    "datetime",
                    "Accelerometer1RMS",
                    "Current",
                    "Pressure",
                    "Temperature",
                    "anomaly",
                }

                missing = required_columns - set(
                    reader.fieldnames or []
                )

                if missing:
                    raise ValueError(
                        f"{file_path.name} is missing columns: "
                        f"{sorted(missing)}"
                    )

                for row in reader:

                    humidity = round(
                        random.uniform(30, 70), 2
                    )

                    readings = {
                        "temperature": float(row["Temperature"]),
                        "vibration": float(row["Accelerometer1RMS"]),
                        "humidity": humidity,
                        "pressure": float(row["Pressure"]),
                        "current": float(row["Current"]),
                    }

                    actual_anomaly = int(float(row["anomaly"]))

                    if actual_anomaly not in (0, 1):
                        raise ValueError(
                            f"Invalid anomaly label in {file_path.name}"
                        )

                    metadata = build_metadata(
                        message_type="sensor_reading",
                        source=SOURCE,
                        run_id=run_id,
                        asset_id=ASSET_ID,
                        units=SENSOR_UNITS[SOURCE],
                        synthetic_fields=SYNTHETIC_FIELDS,
                        source_channels={
                            **SOURCE_CHANNELS,
                            "sequence_id": sequence_id,
                            "sequence_file": file_path.name,
                        },
                        source_timestamp=row["datetime"],
                    )

                    data = {
                        **metadata,
                        "readings": readings,
                        "faults": [],
                        "actual_anomaly": actual_anomaly,
                    }

                    result = client.publish(
                        TOPIC,
                        json.dumps(data),
                        qos=1
                    )

                    result.wait_for_publish()

                    published += 1

                    if published % 1000 == 0:

                        print(
                            "Published records:", published,
                            "| Source time:", row["datetime"],
                            "| Actual anomaly:", actual_anomaly,
                        )

                    time.sleep(0.05)

        print("\nSKAB dataset replay completed!")
        print("Records published:", published)
        print("Run ID:", run_id)

    except KeyboardInterrupt:

        print("\nReplay stopped by user.")

    except Exception as error:

        print("Error:", error)

    finally:

        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    replay()