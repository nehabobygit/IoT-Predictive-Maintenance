import math
import statistics

WINDOW = 10
MIN_HISTORY = 5
Z_THRESHOLD = 1.5
ALERT_COOLDOWN = 30

SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current"
]


def calculate_z_score(history, value, window=WINDOW):
    previous = list(history)[-window:]

    if len(previous) < MIN_HISTORY:
        return None

    if not all(math.isfinite(x) for x in previous):
        return None

    if not math.isfinite(value):
        return None

    mean = statistics.mean(previous)
    std = statistics.stdev(previous)

    if std == 0:
        return None

    return (value - mean) / std


def detect_anomaly(
    history,
    value,
    threshold=Z_THRESHOLD,
    window=WINDOW
):
    score = calculate_z_score(history, value, window)

    return score is not None and abs(score) > threshold


def classify_severity(z_score):
    score = abs(z_score)

    if score >= 5:
        return "HIGH"

    if score >= 3.5:
        return "MEDIUM"

    return "LOW"