"""Compare simulator detectors on disjoint tuning and final seeds."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from detection.detection_engine import WINDOW, calculate_z_score
from detection.hybrid_detector import detect_anomalies, locate_progressive_degradation
from detection.sequence_metrics import aggregate, score_sequence
from sensors.machine_simulator import EPISODE_LENGTH, INTERVAL_SECONDS, PROFILES, SENSORS, MachineSimulator

ROOT = Path(__file__).resolve().parents[1]
OPERATING_POINTS = (None, .75, 1.0, 1.25, 1.5, 1.75)
TIMES = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i*INTERVAL_SECONDS)
         for i in range(EPISODE_LENGTH)]


def collect(seeds):
    scores = {value: [] for value in (*OPERATING_POINTS, "rolling")}
    for seed in seeds:
        for asset in PROFILES:
            simulator = MachineSimulator(asset, seed=seed)
            history = {sensor: [] for sensor in SENSORS}
            truth = []
            predictions = {value: [] for value in scores}
            for _ in TIMES:
                data, faults, _ = simulator.sample()
                truth.append(bool(faults))
                current = bool(detect_anomalies(history, data, progressive_scale=None))
                predictions[None].append(current)
                for scale in OPERATING_POINTS[1:]:
                    predictions[scale].append(current or locate_progressive_degradation(history, data, scale))
                predictions["rolling"].append(any(abs(calculate_z_score(history[key], data[key]) or 0) > 1.5
                                                  for key in SENSORS))
                for key in SENSORS:
                    history[key] = (history[key] + [data[key]])[-WINDOW:]
            for value in scores:
                scores[value].append(score_sequence(truth, predictions[value], TIMES))
    return {value: aggregate(rows) for value, rows in scores.items()}


def main():
    validation = collect(range(500, 515))
    precision_floor = validation[None]["metrics"]["precision"] - .04
    eligible = [value for value in OPERATING_POINTS if validation[value]["metrics"]["precision"] >= precision_floor]
    chosen = max(eligible, key=lambda value: validation[value]["metrics"]["f1_score"])
    test = collect(range(600, 620))
    report = {
        "dataset": "Independent simulated episodes, seeds 600-619",
        "model_type": "Five-sensor hybrid anomaly detector",
        "selection": {"validation_seeds": [500, 514], "precision_floor": precision_floor,
                      "progressive_scale": chosen, "tuning": {str(key): row["metrics"] for key, row in validation.items()}},
        "baseline": test["rolling"], "prior_hybrid": test[None], **test[chosen],
    }
    (ROOT / "results" / "simulator_grouped_metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("selection", "metrics", "confusion_matrix",
           "episodes_detected", "episodes_missed", "detection_delay_seconds_median",
           "false_alarm_episodes_per_8_hours")}, indent=2))


if __name__ == "__main__":
    main()
