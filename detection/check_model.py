
import csv
import pickle
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"
MODEL_PATH = BASE_DIR / "models" / "random_forest.pkl"

FEATURES = [
    "Accelerometer1RMS",
    "Temperature",
    "Current",
    "Pressure"
]

with open(MODEL_PATH, "rb") as file:
    forest = pickle.load(file)


def predict_tree(tree, row):
    current = tree

    while "feature" in current:
        if row[current["feature"]] <= current["threshold"]:
            current = current["left"]
        else:
            current = current["right"]

    return current["prediction"]


print("\n========== FILE-WISE MODEL PERFORMANCE ==========")

for file_number in range(12, 16):
    file_path = DATA_FOLDER / f"{file_number}.csv"

    X_test = []
    y_test = []

    with open(file_path, newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            X_test.append([float(row[name]) for name in FEATURES])
            y_test.append(int(float(row["anomaly"])))

    X_test = np.array(X_test)
    y_test = np.array(y_test)

    predictions = []

    for row in X_test:
        anomaly_votes = sum(
            predict_tree(tree, row) == 1
            for tree in forest
        )

        predictions.append(
            int(anomaly_votes / len(forest) >= 0.2)
        )

    predictions = np.array(predictions)

    tp = int(np.sum((predictions == 1) & (y_test == 1)))
    fp = int(np.sum((predictions == 1) & (y_test == 0)))
    fn = int(np.sum((predictions == 0) & (y_test == 1)))
    tn = int(np.sum((predictions == 0) & (y_test == 0)))

    recall = tp / (tp + fn) if tp + fn else 0
    precision = tp / (tp + fp) if tp + fp else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    print(f"\nFile: {file_number}.csv")
    print("Actual anomalies:", int(np.sum(y_test == 1)))
    print("Detected anomalies:", tp)
    print("False alarms:", fp)
    print("Missed anomalies:", fn)
    print("Recall:", round(recall, 4))
    print("Precision:", round(precision, 4))
    print("F1 Score:", round(f1, 4))

print("\nFile-wise analysis completed!")
