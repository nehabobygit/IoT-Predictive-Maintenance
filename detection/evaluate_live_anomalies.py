"""Benchmark live anomaly rules on 60 seeded simulation episodes."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

from detection.detection_engine import WINDOW
from detection.hybrid_detector import detect_hybrid
from detection.train_ai4i_rf import calculate_metrics
from sensors.machine_simulator import EPISODE_LENGTH, PROFILES, SENSORS, MachineSimulator


def main():
    truth, predictions = [], []
    hits, totals = Counter(), Counter()
    for seed in range(300, 320):
        for asset in PROFILES:
            simulator = MachineSimulator(asset, seed=seed)
            history = {sensor: [] for sensor in SENSORS}
            for _ in range(EPISODE_LENGTH):
                readings, faults, _ = simulator.sample()
                detected = detect_hybrid(history, readings)
                truth.append(int(bool(faults)))
                predictions.append(int(bool(detected)))
                for sensor, category, *_ in faults:
                    totals[category] += 1
                    hits[category] += sensor in detected
                for sensor in SENSORS:
                    history[sensor] = (history[sensor] + [readings[sensor]])[-WINDOW:]
    tp, fp, fn, tn, precision, recall, f1, accuracy = calculate_metrics(
        np.array(truth), np.array(predictions)
    )
    report = {
        "dataset": "60 synthetic episodes with seeds 300–319",
        "test_records": len(truth),
        "metrics": {"accuracy": accuracy, "precision": precision, "recall": recall, "f1_score": f1},
        "confusion_matrix": {"true_positives": tp, "false_positives": fp,
                             "false_negatives": fn, "true_negatives": tn},
        "fault_sensor_hits": {name: {"hits": hits[name], "total": totals[name]} for name in sorted(totals)},
    }
    filename = Path(__file__).resolve().parents[1] / "results" / "live_anomaly_metrics.json"
    filename.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
