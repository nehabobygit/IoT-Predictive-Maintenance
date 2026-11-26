"""Train and evaluate the live simulator model on disjoint runs."""
import json

import numpy as np

from detection.live_maintenance import MODEL_PATH, ROOT, WINDOW, probabilities, window_features
from detection.train_ai4i_improved import choose_threshold, evaluate
from sensors.machine_simulator import EPISODE_LENGTH, HORIZON, PROFILES, SENSORS, MachineSimulator


def samples(seeds):
    features, labels, event_windows = [], [], []
    for seed in seeds:
        for asset in PROFILES:
            simulator = MachineSimulator(asset, seed=seed)
            readings, _, failed = zip(*(simulator.sample() for _ in range(EPISODE_LENGTH)))
            onset = next((i for i, value in enumerate(failed) if value), None)
            event_window = []
            # Exclude points at and shortly after the known simulated breakdown.
            for index in range(WINDOW - 1, EPISODE_LENGTH - HORIZON):
                if onset is not None and onset <= index < onset + WINDOW + 3:
                    continue
                window = [[row[sensor] for sensor in SENSORS]
                          for row in readings[index - WINDOW + 1:index + 1]]
                features.append(window_features(window))
                future_failure = any(failed[index + 1:index + HORIZON + 1])
                labels.append(int(future_failure))
                if future_failure:
                    event_window.append((len(labels) - 1, onset - index))
            if event_window:
                event_windows.append(event_window)
    return np.array(features), np.array(labels), event_windows


def main():
    X, y, _ = samples(range(40))
    validation, validation_y, _ = samples(range(100, 113))
    test, test_y, test_events = samples(range(200, 220))
    center, scale = X.mean(axis=0), X.std(axis=0)
    values = (X - center) / scale
    weights = np.zeros(X.shape[1])
    intercept = 0.0
    sample_weights = np.where(y == 1, 4.0, 1.0)
    for _ in range(650):
        predicted = 1 / (1 + np.exp(-np.clip(values @ weights + intercept, -40, 40)))
        residual = (predicted - y) * sample_weights
        weights -= .15 * (values.T @ residual / len(y) + .004 * weights)
        intercept -= .15 * residual.mean()
    model = {"center": center.tolist(), "scale": scale.tolist(),
             "weights": weights.tolist(), "intercept": float(intercept)}
    model["threshold"] = choose_threshold(validation_y, probabilities(model, validation))
    test_scores = probabilities(model, test)
    leads = [max((lead for index, lead in window if test_scores[index] >= model["threshold"]),
                 default=0) for window in test_events]
    report = {
        "dataset": "Seed-disjoint synthetic machine episodes",
        "model_type": "Weighted logistic regression",
        "horizon_samples": HORIZON,
        "training_records": len(y), "validation_records": len(validation_y),
        "test_records": len(test_y), "test_failures": int(test_y.sum()),
        "failure_episodes": len(leads), "episodes_warned": sum(lead > 0 for lead in leads),
        "median_lead_samples": float(np.median([lead for lead in leads if lead])),
        "decision_threshold": model["threshold"],
        **evaluate(test_y, test_scores, model["threshold"]),
    }
    MODEL_PATH.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    (ROOT / "results" / "live_maintenance_metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
