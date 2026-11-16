
import csv
import pickle
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "models" / "ai4i_random_forest.pkl"
DATA_FILE = BASE_DIR / "data" / "ai4i2020.csv"


def predict_tree(tree, row):
    node = tree

    while node["feature"] is not None:
        if row[node["feature"]] <= node["threshold"]:
            node = node["left"]
        else:
            node = node["right"]

    return node["prediction"]


def predict(model, features):
    scores = []

    for row in features:
        votes = sum(
            predict_tree(tree, row)
            for tree in model["trees"]
        )

        scores.append(votes / len(model["trees"]))

    scores = np.array(scores)

    predictions = (
        scores >= model["threshold"]
    ).astype(int)

    return scores, predictions


def main():
    with open(MODEL_FILE, "rb") as file:
        model = pickle.load(file)

    features = []
    actual = []

    with open(DATA_FILE, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            air = float(row["Air temperature [K]"])
            process = float(row["Process temperature [K]"])
            speed = float(row["Rotational speed [rpm]"])
            torque = float(row["Torque [Nm]"])
            wear = float(row["Tool wear [min]"])

            machine_type = row["Type"]

            features.append([
                air,
                process,
                speed,
                torque,
                wear,
                1 if machine_type == "L" else 0,
                1 if machine_type == "M" else 0,
                1 if machine_type == "H" else 0,
                process - air,
                torque * speed / 1000
            ])

            actual.append(int(row["Machine failure"]))

    X = np.array(features, dtype=float)
    y = np.array(actual, dtype=int)

    scores, predictions = predict(model, X)

    print("\n========== SAVED MODEL PREDICTION TEST ==========")

    print("Total records tested:", len(X))
    print("Predicted failures:", int(np.sum(predictions)))
    print("Predicted normal:", int(len(predictions) - np.sum(predictions)))

    correct = int(np.sum(predictions == y))
    print("Correct predictions:", correct)
    print("Overall accuracy:", round(correct / len(y), 4))

    print("\nFirst 10 predictions:")
    print("Actual | Predicted | Failure score")

    for i in range(10):
        print(
            y[i], "|",
            predictions[i], "|",
            round(float(scores[i]), 3)
        )

    print("\nModel loading and prediction test completed.")


if __name__ == "__main__":
    main()
