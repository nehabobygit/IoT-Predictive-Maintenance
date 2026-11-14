
import csv
import glob
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"

SENSORS = [
    "Accelerometer1RMS",
    "Temperature",
    "Current",
    "Pressure"
]

WINDOW = 10
Z_THRESHOLD = 1.5

TP = 0
FP = 0
FN = 0
TN = 0


def detect_anomaly(history, value):
    if len(history) < 5:
        return False

    mean = statistics.mean(history)
    std = statistics.stdev(history)

    if std == 0:
        return False

    z_score = (value - mean) / std
    return abs(z_score) > Z_THRESHOLD


files = sorted(
    glob.glob(str(DATA_FOLDER / "*.csv")),
    key=lambda path: int(Path(path).stem)
)

print("SKAB Anomaly Detection Evaluation Started\n")

for file_path in files:
    print("Evaluating:", Path(file_path).name)

    histories = {sensor: [] for sensor in SENSORS}

    with open(file_path, newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            actual = int(float(row["anomaly"]))

            predictions = []

            for sensor in SENSORS:
                value = float(row[sensor])
                history = histories[sensor]

                prediction = detect_anomaly(history, value)
                predictions.append(prediction)

                history.append(value)

                if len(history) > WINDOW:
                    history.pop(0)

            predicted = any(predictions)

            if predicted and actual:
                TP += 1
            elif predicted and not actual:
                FP += 1
            elif not predicted and actual:
                FN += 1
            else:
                TN += 1


precision = TP / (TP + FP) if TP + FP else 0
recall = TP / (TP + FN) if TP + FN else 0

f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0
)

accuracy = (TP + TN) / (TP + TN + FP + FN)

print("\n========== EVALUATION RESULTS ==========")
print("True Positives :", TP)
print("False Positives:", FP)
print("False Negatives:", FN)
print("True Negatives :", TN)

print("\nPrecision:", round(precision, 4))
print("Recall   :", round(recall, 4))
print("F1 Score :", round(f1, 4))
print("Accuracy :", round(accuracy, 4))

print("\nEvaluation completed!")
