
import random
import time
from datetime import datetime

def generate_humidity():
    # Normal humidity range
    humidity = round(random.uniform(30.0, 70.0), 2)
    return humidity

print("Humidity Sensor Started")
print("Press Ctrl + C to stop\n")

try:
    while True:
        humidity = generate_humidity()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Time: {timestamp} | Humidity: {humidity}%")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nHumidity Sensor Stopped.")
