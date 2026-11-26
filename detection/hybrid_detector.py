"""Rule-based detection for the simulated sensor stream."""
import statistics
from typing import NamedTuple

from detection.detection_engine import SENSORS


PROGRESSIVE_SCALE = .75


class Anomaly(NamedTuple):
    category: str
    score: float
    explanation: str


def locate_progressive_degradation(history, readings, scale):
    if any(len(history[sensor]) < 7 for sensor in ("temperature", "vibration", "pressure", "current")):
        return False

    def change(sensor):
        recent = history[sensor][-2:] + [readings[sensor]]
        reference = history[sensor][-7:-2]
        return statistics.mean(recent) - statistics.mean(reference)

    return (change("temperature") >= 1.8*scale and change("vibration") >= .65*scale
            and change("pressure") <= -.12*scale and change("current") >= .7*scale)


def detect_anomalies(history, readings, *, progressive_scale=PROGRESSIVE_SCALE):
    anomalies = {}

    def flag(sensor, category, score, explanation):
        if sensor not in anomalies or score > anomalies[sensor].score:
            anomalies[sensor] = Anomaly(category, score, explanation)

    temperature = readings["temperature"]
    vibration = readings["vibration"]
    humidity = readings["humidity"]
    pressure = readings["pressure"]
    current = readings["current"]
    if temperature > 50:
        flag("temperature", "overheating", temperature - 50, "Temperature exceeds 50 °C.")
    if vibration > 8:
        flag("vibration", "irregular_vibration", vibration - 8, "Vibration exceeds 8 mm/s.")
    if pressure < 1.5 or pressure > 6.5:
        flag("pressure", "pressure_variation", max(1.5 - pressure, pressure - 6.5),
             "Pressure is outside the 1.5–6.5 bar operating band.")
    if current > 24:
        flag("current", "current_surge", current - 24, "Current exceeds 24 A.")

    for sensor, recent, minimum, delta, category, two_sided in (
        ("temperature", history["temperature"][-5:], 5, 7, "temperature_rise", False),
        ("humidity", history["humidity"][-10:], 5, 15, "sensor_drift", True),
        ("pressure", history["pressure"][-5:], 5, 1.4, "pressure_variation", True),
    ):
        if len(recent) < minimum:
            continue
        difference = readings[sensor] - statistics.mean(recent)
        deviation = abs(difference) if two_sided else difference
        if deviation > delta:
            flag(sensor, category, deviation - delta,
                 f"Reading changed by {difference:+.1f} from its recent mean.")

    for sensor, value, step, total, category in (
        ("temperature", temperature, 1.5, 8, "temperature_rise"),
        ("humidity", humidity, 1.0, 11, "sensor_drift"),
    ):
        series = history[sensor][-5:] + [value]
        if len(series) < 6:
            continue
        direction = -1 if sensor == "humidity" and value < series[0] else 1
        drift = direction * (value - series[0])
        if drift >= total and all(direction * (b - a) >= step for a, b in zip(series, series[1:])):
            flag(sensor, category, max(drift - total, .01),
                 f"Reading trended consistently by {value - series[0]:+.1f} over five intervals.")
    if progressive_scale is not None and locate_progressive_degradation(history, readings, progressive_scale):
        if "vibration" not in anomalies:
            flag("vibration", "progressive_degradation", 1.0,
                 "Vibration, temperature and current rose as pressure fell across recent windows.")
    return anomalies


def detect_hybrid(history, readings):
    """Return sensor-to-score mappings for the original evaluation scripts."""
    return {sensor: finding.score for sensor, finding in detect_anomalies(history, readings, progressive_scale=None).items()}
