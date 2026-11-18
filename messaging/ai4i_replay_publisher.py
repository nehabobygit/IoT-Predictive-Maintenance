
import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt


BROKER = "localhost"
PORT = 1883
TOPIC = "factory/ai4i/replay"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "ai4i2020.csv"


def create_message(row):
    machine_type = row["Type"]

    if machine_type not in ("L", "M", "H"):
        raise ValueError(f"Invalid machine type: {machine_type}")

    return {
        "message_type": "ai4i_replay",
        "timestamp": datetime.now().isoformat(),
        "udi": int(row["ï»¿UDI"]) if "ï»¿UDI" in row else int(row["UDI"]),
        "product_id": row["Product ID"],
        "machine_type": machine_type,
        "readings": {
            "air_temperature": float(row["Air temperature [K]"]),
            "process_temperature": float(row["Process temperature [K]"]),
            "rotational_speed": float(row["Rotational speed [rpm]"]),
            "torque": float(row["Torque [Nm]"]),
            "tool_wear": float(row["Tool wear [min]"])
        },
        "actual_failure": int(row["Machine failure"])
    }


def main():
    parser = argparse.ArgumentParser(
        description="Replay AI4I machine records through MQTT."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum records to publish. Use 0 for all records."
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Delay between published records in seconds."
    )

    args = parser.parse_args()

    if args.limit < 0 or args.interval < 0:
        raise ValueError("Limit and interval cannot be negative.")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("AI4I MQTT Replay Publisher Started")
        print("Dataset:", DATA_FILE)
        print("MQTT topic:", TOPIC)
        print("Record limit:", args.limit if args.limit else "All records")
        print("Publishing interval:", args.interval, "seconds\n")

        published = 0
        actual_failures = 0

        with open(DATA_FILE, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:

                if args.limit and published >= args.limit:
                    break

                message = create_message(row)

                result = client.publish(
                    TOPIC,
                    json.dumps(message),
                    qos=1
                )

                result.wait_for_publish()

                published += 1
                actual_failures += message["actual_failure"]

                print(
                    f"Published UDI {message['udi']} | "
                    f"Machine: {message['machine_type']} | "
                    f"Actual failure: {message['actual_failure']}"
                )

                if args.interval:
                    time.sleep(args.interval)

        print("\n========== REPLAY SUMMARY ==========")
        print("Records published:", published)
        print("Actual failure records:", actual_failures)
        print("Actual normal records:", published - actual_failures)
        print("Replay completed.")

    except KeyboardInterrupt:
        print("\nReplay interrupted by user.")

    except Exception as error:
        print("\nPublisher error:", error)

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
