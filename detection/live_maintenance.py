"""Predict simulated degradation onset using recent sensor history."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from sensors.machine_simulator import HORIZON, INTERVAL_SECONDS, SENSORS

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "live_maintenance.json"
WINDOW = 10
CHANNELS = [SENSORS.index(sensor) for sensor in ("temperature", "vibration", "pressure", "current")]


def window_features(rows):
    # Compare two trailing windows and measure short-window spread. Humidity
    # drift is a sensor fault in the simulator and does not cause motor wear.
    readings = np.asarray(rows, dtype=float)[:, CHANNELS]
    previous, recent = readings[:5], readings[5:]
    return np.r_[recent.mean(axis=0), recent.mean(axis=0) - previous.mean(axis=0),
                 recent.std(axis=0)]


def probabilities(model, features):
    standardized = (features - model["center"]) / model["scale"]
    logits = np.clip(standardized @ model["weights"] + model["intercept"], -40, 40)
    return 1 / (1 + np.exp(-logits))


@lru_cache(maxsize=1)
def load_model():
    with MODEL_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def forecast(rows):
    if len(rows) < WINDOW:
        return None
    model = load_model()
    score = float(probabilities(model, window_features(rows)))
    return score, model["threshold"], HORIZON * INTERVAL_SECONDS
