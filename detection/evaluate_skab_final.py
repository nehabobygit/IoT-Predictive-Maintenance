import csv
import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from detection.detection_engine import calculate_z_score

DATA = ROOT / "data" / "SKAB-master" / "data" / "valve1"

TEST_FILES = [0, 3, 11]

SENSORS = [
    "Accelerometer1RMS",
    "Temperature",
    "Current",
    "Pressure"
]

BASELINE_SIZE = 100
REFERENCE_WINDOW = 30
REFERENCE_THRESHOLD = 5

ROLLING_WINDOW = 10
ROLLING_THRESHOLD = 1.5


def calculate_metrics(actual, predicted):

    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    tp = int(np.sum((actual == 1) & (predicted == 1)))
    fp = int(np.sum((actual == 0) & (predicted == 1)))
    fn = int(np.sum((actual == 1) & (predicted == 0)))
    tn = int(np.sum((actual == 0) & (predicted == 0)))

    delays = []
    missed_episodes = 0
    i = 0

    while i < len(actual):

        if actual[i] == 0:
            i += 1
            continue

        start = i

        while i < len(actual) and actual[i] == 1:
            i += 1

        detected = np.flatnonzero(predicted[start:i])

        if len(detected):
            delays.append(int(detected[0]))
        else:
            missed_episodes += 1

    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": tp / max(tp + fp, 1),
        "recall": tp / max(tp + fn, 1),
        "f1": 2 * tp / max(2 * tp + fp + fn, 1),
        "accuracy": (tp + tn) / max(len(actual), 1),
        "false_positive_rate": fp / max(fp + tn, 1),
        "false_positives_per_1000_readings":
            1000 * fp / max(len(actual), 1),
        "detected_episodes": len(delays),
        "missed_episodes": missed_episodes,
        "mean_detection_delay_samples":
            float(np.mean(delays)) if delays else None,
        "detection_delays_samples": delays
    }


def print_metrics(metrics):

    for key, value in metrics.items():

        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")


report = {
    "dataset": "SKAB valve1",
    "validation_files": [15, 4],
    "test_files": TEST_FILES,
    "warmup_excluded_per_file": BASELINE_SIZE,
    "rolling_configuration": {
        "window": ROLLING_WINDOW,
        "threshold": ROLLING_THRESHOLD
    },
    "reference_configuration": {
        "baseline": BASELINE_SIZE,
        "window": REFERENCE_WINDOW,
        "threshold": REFERENCE_THRESHOLD
    },
    "per_file": {},
    "overall": {},
    "limitations": [
        "Test files were used in earlier project experiments.",
        "Results measure point-level detection before alert cooldown.",
        "Detection delay is measured in samples, not seconds.",
        "Fixed reference requires a healthy calibration period.",
        "Results do not establish industrial deployment readiness."
    ]
}

methods = ["rolling_z", "fixed_reference"]

aggregate = {
    method: {
        "actual": [],
        "predicted": [],
        "delays": [],
        "missed": 0
    }
    for method in methods
}

for number in TEST_FILES:

    filename = f"{number}.csv"

    with open(
        DATA / filename,
        newline="",
        encoding="utf-8-sig"
    ) as file:

        rows = list(csv.DictReader(file, delimiter=";"))

    X = np.array([
        [float(row[sensor]) for sensor in SENSORS]
        for row in rows
    ])

    y = np.array([
        int(float(row["anomaly"]))
        for row in rows
    ])

    reference = X[:BASELINE_SIZE]

    mean = np.mean(reference, axis=0)
    std = np.maximum(np.std(reference, axis=0), 1e-8)

    predictions = {
        method: [] for method in methods
    }

    actual = y[BASELINE_SIZE:]

    for i in range(BASELINE_SIZE, len(X)):

        rolling_scores = []

        for channel in range(len(SENSORS)):

            score = calculate_z_score(
                X[i-ROLLING_WINDOW:i, channel],
                X[i, channel],
                ROLLING_WINDOW
            )

            if score is not None:
                rolling_scores.append(abs(score))

        rolling_prediction = int(
            max(rolling_scores, default=0)
            > ROLLING_THRESHOLD
        )

        recent = X[i-REFERENCE_WINDOW+1:i+1]

        reference_score = np.max(
            np.abs(np.mean(recent, axis=0) - mean) / std
        )

        reference_prediction = int(
            reference_score > REFERENCE_THRESHOLD
        )

        predictions["rolling_z"].append(
            rolling_prediction
        )

        predictions["fixed_reference"].append(
            reference_prediction
        )

    report["per_file"][filename] = {
        "calibration_anomalies":
            int(np.sum(y[:BASELINE_SIZE]))
    }

    print(f"\n========== {filename} ==========")

    print(
        "Calibration anomalies:",
        int(np.sum(y[:BASELINE_SIZE]))
    )

    for method in methods:

        metrics = calculate_metrics(
            actual,
            predictions[method]
        )

        report["per_file"][filename][method] = metrics

        aggregate[method]["actual"].extend(actual)
        aggregate[method]["predicted"].extend(
            predictions[method]
        )
        aggregate[method]["delays"].extend(
            metrics["detection_delays_samples"]
        )
        aggregate[method]["missed"] += (
            metrics["missed_episodes"]
        )

        print("\nMethod:", method)
        print_metrics(metrics)


print("\n========== OVERALL TEST RESULTS ==========")

for method in methods:

    data = aggregate[method]

    metrics = calculate_metrics(
        data["actual"],
        data["predicted"]
    )

    # Preserve individual experiment boundaries.
    metrics["detected_episodes"] = len(data["delays"])
    metrics["missed_episodes"] = data["missed"]

    metrics["mean_detection_delay_samples"] = (
        float(np.mean(data["delays"]))
        if data["delays"] else None
    )

    metrics["detection_delays_samples"] = data["delays"]

    report["overall"][method] = metrics

    print("\nMethod:", method)
    print_metrics(metrics)


output = ROOT / "results" / "skab_final_evaluation.json"

output.parent.mkdir(exist_ok=True)

with open(output, "w", encoding="utf-8") as file:
    json.dump(report, file, indent=4)

print("\nReport saved:", output)
print("Evaluation completed.")