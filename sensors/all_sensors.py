
import random
import time
from datetime import datetime

def generate_readings():
    return {
        "temperature": round(random.uniform(35.0, 45.0), 2),
        "vibration": round(random.uniform(1.0, 5.0), 2),
        "humidity": round(random.uniform(30.0, 70.0), 2),
        "pressure": round(random.uniform(2.0, 6.0), 2),
        "current": round(random.uniform(5.0, 20.0), 2)
    }

print("IoT Predictive Maintenance - Sensor Network")
print("All 5 sensors are running")
print("Press Ctrl + C to stop\n")

try:
    while True:
        readings = generate_readings()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("-" * 55)
        print("Timestamp:", timestamp)

        for sensor, value in readings.items():
            print(f"{sensor.capitalize()}: {value}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nAll sensors stopped.")
