import os
import csv
import json
import random
import time
from pathlib import Path

import paho.mqtt.client as mqtt

try:
    from .message_contract import (
        SENSOR_UNITS,
        build_metadata,
        new_id,
    )
except ImportError:
    from message_contract import (
        SENSOR_UNITS,
        build_metadata,
        new_id,
    )

try:
    from .mqtt_security import configure_mqtt_auth
except ImportError:
    from mqtt_security import configure_mqtt_auth

BROKER = os.getenv("MQTT_HOST", "localhost")
PORT = 8883
TOPIC = "factory/sensors"

BASE_DIR = Path(__file__).resolve().parent.parent
FAULT_LOG = BASE_DIR / "data" / "fault_log.csv"
FAULT_LOG_V2 = BASE_DIR / "data" / "fault_log_v2.csv"

ASSET_ID = "SIM-MOTOR-001"
SOURCE = "simulated_sensor"

SOURCE_CHANNELS = {
    "temperature": "simulated_temperature",
    "vibration": "simulated_vibration",
    "humidity": "simulated_humidity",
    "pressure": "simulated_pressure",
    "current": "simulated_current",
}

SYNTHETIC_FIELDS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current",
]

FAULT_LOG_V2_FIELDS = [
    "timestamp",
    "event_id",
    "run_id",
    "asset_id",
    "source",
    "sensor",
    "fault_type",
    "normal_value",
    "fault_value",
    "unit",
]

cycle = 0
gradual_rise = 0
humidity_drift = 0


def append_fault_logs(metadata, faults):
    """Append to the legacy log and a metadata-complete log."""
    if not faults:
        return

    FAULT_LOG.parent.mkdir(parents=True, exist_ok=True)

    # Preserve the existing five-column log format.
    with open(FAULT_LOG, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        for sensor, fault_type, normal, faulty in faults:
            writer.writerow([
                metadata["timestamp"],
                sensor,
                fault_type,
                normal,
                faulty,
            ])

    FAULT_LOG_V2.parent.mkdir(parents=True, exist_ok=True)

    needs_header = (
        not FAULT_LOG_V2.exists()
        or FAULT_LOG_V2.stat().st_size == 0
    )

    with open(FAULT_LOG_V2, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FAULT_LOG_V2_FIELDS,
        )

        if needs_header:
            writer.writeheader()

        for sensor, fault_type, normal, faulty in faults:
            writer.writerow({
                "timestamp": metadata["timestamp"],
                "event_id": metadata["event_id"],
                "run_id": metadata["run_id"],
                "asset_id": metadata["asset_id"],
                "source": metadata["source"],
                "sensor": sensor,
                "fault_type": fault_type,
                "normal_value": normal,
                "fault_value": faulty,
                "unit": SENSOR_UNITS[SOURCE][sensor],
            })


def generate_readings(run_id):
    global cycle, gradual_rise, humidity_drift

    cycle += 1

    readings = {
        "temperature": round(random.uniform(35, 45), 2),
        "vibration": round(random.uniform(1, 5), 2),
        "humidity": round(random.uniform(30, 70), 2),
        "pressure": round(random.uniform(2, 6), 2),
        "current": round(random.uniform(5, 20), 2),
    }

    faults = []

    # 1. Sudden temperature spike
    if cycle % 40 == 5:
        normal = readings["temperature"]

        readings["temperature"] = round(
            normal + 25,
            2,
        )

        faults.append((
            "temperature",
            "sudden_spike",
            normal,
            readings["temperature"],
        ))

    # 2. Gradual temperature rise
    if cycle % 40 in range(10, 15):
        gradual_rise += 1

        normal = readings["temperature"]

        readings["temperature"] = round(
            normal + gradual_rise * 4,
            2,
        )

        faults.append((
            "temperature",
            "gradual_rise",
            normal,
            readings["temperature"],
        ))

    elif cycle % 40 == 15:
        gradual_rise = 0

    # 3. Irregular vibration
    if cycle % 40 == 20:
        normal = readings["vibration"]

        readings["vibration"] = round(
            random.uniform(12, 18),
            2,
        )

        faults.append((
            "vibration",
            "irregular_vibration",
            normal,
            readings["vibration"],
        ))

    # 4. Slow humidity sensor drift
    if cycle % 40 in range(25, 35):
        humidity_drift += 1.5

        normal = readings["humidity"]

        readings["humidity"] = round(
            min(normal + humidity_drift, 100),
            2,
        )

        faults.append((
            "humidity",
            "sensor_drift",
            normal,
            readings["humidity"],
        ))

    # 5. Abnormal pressure drop
    if cycle % 40 == 36:
        normal = readings["pressure"]

        readings["pressure"] = round(
            random.uniform(0.4, 1.2),
            2,
        )

        faults.append((
            "pressure",
            "pressure_drop",
            normal,
            readings["pressure"],
        ))

    # 6. Electrical current surge
    if cycle % 40 == 38:
        normal = readings["current"]

        readings["current"] = round(
            random.uniform(25, 32),
            2,
        )

        faults.append((
            "current",
            "current_surge",
            normal,
            readings["current"],
        ))

    metadata = build_metadata(
        message_type="sensor_reading",
        source=SOURCE,
        run_id=run_id,
        asset_id=ASSET_ID,
        units=SENSOR_UNITS[SOURCE],
        synthetic_fields=SYNTHETIC_FIELDS,
        source_channels=SOURCE_CHANNELS,
    )

    data = {
        **metadata,
        "readings": readings,
        "faults": [fault[1] for fault in faults],
        "actual_anomaly": 1 if faults else 0,
    }

    if faults:
        append_fault_logs(metadata, faults)

        for sensor, fault_type, _, _ in faults:
            print(
                "FAULT INJECTED:",
                fault_type,
                "|",
                sensor,
            )

    return data


def main():
    run_id = new_id()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    try:
        configure_mqtt_auth(client, "publisher")

        client.connect(
            BROKER,
            PORT,
            60,
        )

        client.loop_start()

        print("Fault Injection Publisher Started")
        print("MQTT topic:", TOPIC)
        print("Asset ID:", ASSET_ID)
        print("Source:", SOURCE)
        print("Run ID:", run_id)
        print("Generating normal and faulty readings...\n")

        while True:
            data = generate_readings(run_id)

            result = client.publish(
                TOPIC,
                json.dumps(data),
                qos=1,
            )

            result.wait_for_publish()

            print("Published:", json.dumps(data))

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nPublisher stopped.")

    except Exception as error:
        print("Error:", error)

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
