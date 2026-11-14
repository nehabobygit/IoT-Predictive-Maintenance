
import json
import random
import time
import csv
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/sensors"

BASE_DIR = Path(__file__).resolve().parent.parent
FAULT_LOG = BASE_DIR / "data" / "fault_log.csv"

cycle = 0
gradual_rise = 0
humidity_drift = 0

def generate_readings():
    global cycle, gradual_rise, humidity_drift

    cycle += 1

    readings = {
        "temperature": round(random.uniform(35, 45), 2),
        "vibration": round(random.uniform(1, 5), 2),
        "humidity": round(random.uniform(30, 70), 2),
        "pressure": round(random.uniform(2, 6), 2),
        "current": round(random.uniform(5, 20), 2)
    }

    faults = []

    # 1. Sudden temperature spike
    if cycle % 40 == 5:
        normal = readings["temperature"]
        readings["temperature"] = round(normal + 25, 2)
        faults.append(("temperature", "sudden_spike",
                       normal, readings["temperature"]))

    # 2. Gradual temperature rise over five readings
    if cycle % 40 in range(10, 15):
        gradual_rise += 1
        normal = readings["temperature"]
        readings["temperature"] = round(normal + gradual_rise * 4, 2)
        faults.append(("temperature", "gradual_rise",
                       normal, readings["temperature"]))
    elif cycle % 40 == 15:
        gradual_rise = 0

    # 3. Irregular vibration
    if cycle % 40 == 20:
        normal = readings["vibration"]
        readings["vibration"] = round(random.uniform(12, 18), 2)
        faults.append(("vibration", "irregular_vibration",
                       normal, readings["vibration"]))

    # 4. Slow humidity sensor drift
    if cycle % 40 in range(25, 35):
        humidity_drift += 1.5
        normal = readings["humidity"]
        readings["humidity"] = round(
            min(normal + humidity_drift, 100), 2
        )
        faults.append(("humidity", "sensor_drift",
                       normal, readings["humidity"]))

    timestamp = datetime.now().isoformat()

    # Record injected faults
    if faults:
        with open(FAULT_LOG, "a", newline="") as file:
            writer = csv.writer(file)

            for sensor, fault_type, normal, faulty in faults:
                writer.writerow([
                    timestamp, sensor, fault_type, normal, faulty
                ])
                print("FAULT INJECTED:", fault_type, "|", sensor)

    return {
        "timestamp": timestamp,
        "readings": readings,
        "faults": [fault[1] for fault in faults]
    }


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print("Fault Injection Publisher Started")
    print("Generating normal and faulty readings...\n")

    while True:
        data = generate_readings()
        client.publish(TOPIC, json.dumps(data))

        print("Published:", json.dumps(data))
        time.sleep(2)

except KeyboardInterrupt:
    print("\nPublisher stopped.")

except Exception as e:
    print("Error:", e)

finally:
    client.loop_stop()
    client.disconnect()
