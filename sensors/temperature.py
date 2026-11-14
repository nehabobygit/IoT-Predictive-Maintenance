
import random
import time
from datetime import datetime

def generate_temperature():
    # Normal operating temperature range
    temperature = round(random.uniform(35.0, 45.0), 2)
    return temperature

print("Temperature Sensor Started")
print("Press Ctrl + C to stop\n")

try:
    while True:
        temperature = generate_temperature()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Time: {timestamp} | Temperature: {temperature} °C")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nTemperature Sensor Stopped.")
