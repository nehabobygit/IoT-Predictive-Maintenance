import os
import csv
import json
import time
from pathlib import Path

from sensors.machine_simulator import INTERVAL_SECONDS, PROFILES, MachineSimulator

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
    from .mqtt_security import connect_configured
except ImportError:
    from mqtt_security import connect_configured

TOPIC = "factory/sensors"

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.getenv("IOT_FAULT_LOG_DIR", BASE_DIR / "data"))
FAULT_LOG = LOG_DIR / "fault_log.csv"
FAULT_LOG_V2 = LOG_DIR / "fault_log_v2.csv"

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

default_simulators = {asset: MachineSimulator(asset) for asset in PROFILES}


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


def generate_readings(run_id, asset_id=ASSET_ID, simulator=None):
    readings, faults, _ = (simulator or default_simulators[asset_id]).sample()

    metadata = build_metadata(
        message_type="sensor_reading",
        source=SOURCE,
        run_id=run_id,
        asset_id=asset_id,
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
    ready = Path("/tmp/iot-publisher-ready") if os.getenv("DOCKER_ENV") == "1" else None
    if ready:
        ready.unlink(missing_ok=True)
    run_id = new_id()
    simulators = {
        asset: MachineSimulator(asset, offset=offset)
        for asset, offset in zip(PROFILES, (0, 5, 10))
    }

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    try:
        connect_configured(client, "publisher", asynchronous=True)

        client.loop_start()

        print("Fault Injection Publisher Started")
        print("MQTT topic:", TOPIC)
        print("Assets:", ", ".join(simulators))
        print("Source:", SOURCE)
        print("Run ID:", run_id)
        print("Generating normal and faulty readings...\n")

        while True:
            for asset, simulator in simulators.items():
                data = generate_readings(run_id, asset, simulator)
                while True:
                    if not client.is_connected():
                        time.sleep(1)
                        continue
                    result = client.publish(TOPIC, json.dumps(data), qos=1)
                    try:
                        result.wait_for_publish(timeout=10)
                    except RuntimeError:
                        if result.rc != mqtt.MQTT_ERR_NO_CONN:
                            raise
                        continue
                    while not result.is_published():
                        result.wait_for_publish(timeout=10)
                    break
                if ready:
                    ready.touch()
                print("Published:", data["asset_id"], data["timestamp"], data["readings"])
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nPublisher stopped.")

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
