
import random
import time
from datetime import datetime

def generate_vibration():
    # Normal machine vibration range
    vibration = round(random.uniform(1.0, 5.0), 2)
    return vibration

print("Vibration Sensor Started")
print("Press Ctrl + C to stop\n")

try:
    while True:
        vibration = generate_vibration()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Time: {timestamp} | Vibration: {vibration} mm/s")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nVibration Sensor Stopped.")
