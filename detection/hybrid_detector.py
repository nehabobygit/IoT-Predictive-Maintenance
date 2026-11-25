
import statistics

SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current",
]


def detect_hybrid(history, readings):
    """
    Detect simulated sensor anomalies.

    Returns a dictionary mapping sensor names
    to positive anomaly scores.
    """
    anomalies = {}

    temperature = readings["temperature"]
    vibration = readings["vibration"]
    humidity = readings["humidity"]
    pressure = readings["pressure"]
    current = readings["current"]

    # 1. Sudden temperature spikes
    if temperature > 50:
        anomalies["temperature"] = temperature - 50

    # 2. Irregular vibration
    if vibration > 8:
        anomalies["vibration"] = vibration - 8

    # 3. Temperature increase relative to recent history
    recent_temperature = history["temperature"][-5:]

    if len(recent_temperature) == 5:
        mean_temperature = statistics.mean(recent_temperature)

        if temperature > mean_temperature + 7:
            anomalies["temperature"] = max(
                anomalies.get("temperature", 0),
                temperature - mean_temperature - 7,
            )

    # 4. Gradual temperature rise
    temperature_series = history["temperature"][-5:] + [temperature]

    if len(temperature_series) == 6:
        changes = [
            temperature_series[i + 1] - temperature_series[i]
            for i in range(5)
        ]

        if (
            all(change >= 1.5 for change in changes)
            and temperature_series[-1] - temperature_series[0] >= 8
        ):
            anomalies["temperature"] = max(
                anomalies.get("temperature", 0),
                temperature_series[-1] - temperature_series[0] - 8,
                0.01,
            )

    # 5. Humidity increase relative to recent history
    recent_humidity = history["humidity"][-10:]

    if len(recent_humidity) >= 5:
        mean_humidity = statistics.mean(recent_humidity)

        if humidity > mean_humidity + 15:
            anomalies["humidity"] = humidity - mean_humidity - 15

    # 6. Sustained humidity drift
    humidity_series = history["humidity"][-5:] + [humidity]

    if len(humidity_series) == 6:
        changes = [
            humidity_series[i + 1] - humidity_series[i]
            for i in range(5)
        ]

        if (
            all(change >= 2 for change in changes)
            and humidity_series[-1] - humidity_series[0] >= 12
        ):
            anomalies["humidity"] = max(
                anomalies.get("humidity", 0),
                humidity_series[-1] - humidity_series[0] - 12,
                0.01,
            )

    # 7. Abnormal pressure drop
    if pressure < 1.5:
        anomalies["pressure"] = 1.5 - pressure

    # 8. Electrical current surge
    if current > 24:
        anomalies["current"] = current - 24

    return anomalies
