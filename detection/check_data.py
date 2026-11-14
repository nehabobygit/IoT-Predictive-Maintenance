
import csv
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"

FEATURES = [
    "Accelerometer1RMS",
    "Temperature",
    "Current",
    "Pressure"
]

print("\n========== ALL FILES: ANOMALY PATTERNS ==========")

for file_number in range(16):
    file_path = DATA_FOLDER / f"{file_number}.csv"

    groups = {
        "Normal": {sensor: [] for sensor in FEATURES},
        "Anomaly": {sensor: [] for sensor in FEATURES}
    }

    with open(file_path, newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            category = (
                "Anomaly"
                if int(float(row["anomaly"])) == 1
                else "Normal"
            )

            for sensor in FEATURES:
                groups[category][sensor].append(
                    float(row[sensor])
                )

    print(f"\nFile {file_number}.csv")

    for sensor in FEATURES:
        normal = groups["Normal"][sensor]
        anomaly = groups["Anomaly"][sensor]

        normal_mean = statistics.mean(normal)
        anomaly_mean = statistics.mean(anomaly)

        difference = anomaly_mean - normal_mean

        print(
            sensor,
            "| Normal:", round(normal_mean, 5),
            "| Anomaly:", round(anomaly_mean, 5),
            "| Difference:", round(difference, 5)
        )

print("\nComplete dataset analysis finished!")
