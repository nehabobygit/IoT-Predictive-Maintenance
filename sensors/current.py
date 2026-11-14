
import random
import time
from datetime import datetime

def generate_current():
    # Normal operating current range in amperes
    current = round(random.uniform(5.0, 20.0), 2)
    return current

print("Current Sensor Started")
print("Press Ctrl + C to stop\n")

try:
    while True:
        current = generate_current()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Time: {timestamp} | Current: {current} A")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nCurrent Sensor Stopped.")
