
import random
import time
from datetime import datetime

def generate_pressure():
    # Normal operating pressure range in bar
    pressure = round(random.uniform(2.0, 6.0), 2)
    return pressure

print("Pressure Sensor Started")
print("Press Ctrl + C to stop\n")

try:
    while True:
        pressure = generate_pressure()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Time: {timestamp} | Pressure: {pressure} bar")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nPressure Sensor Stopped.")
