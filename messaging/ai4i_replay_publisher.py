import argparse
import csv
import json
import time
from pathlib import Path

import paho.mqtt.client as mqtt

try:
    from .message_contract import AI4I_UNITS, build_metadata, new_id
except ImportError:
    from message_contract import AI4I_UNITS, build_metadata, new_id

try:
    from .mqtt_security import configure_mqtt_auth
except ImportError:
    from mqtt_security import configure_mqtt_auth

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/ai4i/replay"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "ai4i2020.csv"

SOURCE = "ai4i_replay"
SOURCE_CHANNELS = {
    "air_temperature": "Air temperature [K]",
    "process_temperature": "Process temperature [K]",
    "rotational_speed": "Rotational speed [rpm]",
    "torque": "Torque [Nm]",
    "tool_wear": "Tool wear [min]",
    "machine_type": "Type",
    "actual_failure": "Machine failure",
}
SYNTHETIC_FIELDS = [
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
    "machine_type",
    "actual_failure",
]


def create_message(row, run_id):
    machine_type = row["Type"]
    if machine_type not in ("L", "M", "H"):
        raise ValueError(f"Invalid machine type: {machine_type}")

    try:
        udi = int(row["UDI"])
        actual_failure = int(row["Machine failure"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("AI4I record has an invalid UDI or failure label.") from error

    if actual_failure not in (0, 1):
        raise ValueError("AI4I failure label must be 0 or 1.")

    readings = {
        "air_temperature": float(row["Air temperature [K]"]),
        "process_temperature": float(row["Process temperature [K]"]),
        "rotational_speed": float(row["Rotational speed [rpm]"]),
        "torque": float(row["Torque [Nm]"]),
        "tool_wear": float(row["Tool wear [min]"]),
    }

    metadata = build_metadata(
        message_type="ai4i_replay",
        source=SOURCE,
        run_id=run_id,
        # AI4I contains synthetic product records but no physical asset ID.
        asset_id=None,
        units=AI4I_UNITS,
        synthetic_fields=SYNTHETIC_FIELDS,
        source_channels=SOURCE_CHANNELS,
        source_timestamp=None,
    )

    return {
        **metadata,
        "udi": udi,
        "product_id": row["Product ID"],
        "machine_type": machine_type,
        "readings": readings,
        "actual_failure": actual_failure,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Replay AI4I machine records through MQTT."
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Maximum records to publish. Use 0 for all records.",
    )
    parser.add_argument(
        "--interval", type=float, default=0.5,
        help="Delay between published records in seconds.",
    )
    args = parser.parse_args()

    if args.limit < 0 or args.interval < 0:
        raise ValueError("Limit and interval cannot be negative.")
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    run_id = new_id()
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    try:
        configure_mqtt_auth(client, "publisher")
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("AI4I MQTT Replay Publisher Started")
        print("Dataset:", DATA_FILE)
        print("MQTT topic:", TOPIC)
        print("Source:", SOURCE)
        print("Asset ID: Not supplied by AI4I dataset (stored as NULL)")
        print("Run ID:", run_id)
        print("Record limit:", args.limit if args.limit else "All records")
        print("Publishing interval:", args.interval, "seconds\n")

        published = 0
        actual_failures = 0

        with open(DATA_FILE, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            required = {
                "UDI", "Product ID", "Type", "Air temperature [K]",
                "Process temperature [K]", "Rotational speed [rpm]",
                "Torque [Nm]", "Tool wear [min]", "Machine failure",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"AI4I CSV is missing columns: {sorted(missing)}")

            for row in reader:
                if args.limit and published >= args.limit:
                    break

                message = create_message(row, run_id)
                result = client.publish(TOPIC, json.dumps(message), qos=1)
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
        print("Run ID:", run_id)
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
