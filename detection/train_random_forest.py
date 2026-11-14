
import csv
import random
import pickle
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data" / "SKAB-master" / "data" / "valve1"
MODEL_FOLDER = BASE_DIR / "models"

FEATURES = [
    "Accelerometer1RMS",
    "Temperature",
    "Current",
    "Pressure"
]

WINDOW_SIZE = 5

random.seed(42)
np.random.seed(42)


def create_temporal_features(readings):
    """
    Creates features using:
    1. Current sensor readings
    2. Change from the previous reading
    3. Rolling mean of the last 5 readings
    4. Rolling standard deviation of the last 5 readings
    """

    result = []

    for i in range(len(readings)):
        current = readings[i]

        if i == 0:
            previous = current
        else:
            previous = readings[i - 1]

        changes = current - previous

        start = max(0, i - WINDOW_SIZE + 1)
        window = readings[start:i + 1]

        rolling_mean = np.mean(window, axis=0)
        rolling_std = np.std(window, axis=0)

        combined = np.concatenate([
            current,
            changes,
            rolling_mean,
            rolling_std
        ])

        result.append(combined)

    return result


def gini(labels):
    if len(labels) == 0:
        return 0

    probabilities = np.bincount(labels, minlength=2) / len(labels)
    return 1 - np.sum(probabilities ** 2)


def build_tree(X, y, depth=0, max_depth=6):
    counts = np.bincount(y, minlength=2)
    prediction = int(np.argmax(counts))

    node = {"prediction": prediction}

    if depth >= max_depth or len(y) < 20 or len(np.unique(y)) == 1:
        return node

    feature_count = max(1, int(np.sqrt(X.shape[1])))

    selected_features = np.random.choice(
        X.shape[1], feature_count, replace=False
    )

    best_score = float("inf")
    best_split = None

    for feature in selected_features:
        values = X[:, feature]

        thresholds = np.unique(
            np.quantile(values, np.linspace(0.1, 0.9, 9))
        )

        for threshold in thresholds:
            left_mask = values <= threshold
            right_mask = ~left_mask

            if left_mask.sum() < 5 or right_mask.sum() < 5:
                continue

            left_y = y[left_mask]
            right_y = y[right_mask]

            score = (
                len(left_y) * gini(left_y)
                + len(right_y) * gini(right_y)
            ) / len(y)

            if score < best_score:
                best_score = score
                best_split = (feature, threshold, left_mask)

    if best_split is None:
        return node

    feature, threshold, left_mask = best_split

    node["feature"] = int(feature)
    node["threshold"] = float(threshold)

    node["left"] = build_tree(
        X[left_mask], y[left_mask], depth + 1, max_depth
    )

    node["right"] = build_tree(
        X[~left_mask], y[~left_mask], depth + 1, max_depth
    )

    return node


def predict_tree(tree, row):
    if "feature" not in tree:
        return tree["prediction"]

    if row[tree["feature"]] <= tree["threshold"]:
        return predict_tree(tree["left"], row)

    return predict_tree(tree["right"], row)


def train_random_forest(X, y, tree_count=20):
    forest = []

    print("\nTraining Temporal Random Forest...")

    for i in range(tree_count):
        indices = np.random.choice(
            len(X), size=min(5000, len(X)), replace=True
        )

        tree = build_tree(X[indices], y[indices])
        forest.append(tree)

        print(f"Tree {i + 1}/{tree_count} trained")

    return forest


def predict_forest(forest, X):
    predictions = []

    for row in X:
        votes = [predict_tree(tree, row) for tree in forest]
        predictions.append(int(np.mean(votes) >= 0.5))

    return np.array(predictions)


def main():
    files = sorted(
        DATA_FOLDER.glob("*.csv"),
        key=lambda path: int(path.stem)
    )

    if len(files) < 2:
        print("Error: SKAB CSV files not found.")
        return

    X_train, y_train = [], []
    X_test, y_test = [], []

    print("Loading SKAB dataset and creating temporal features...")

    for file_path in files:
        is_training = int(file_path.stem) < 12

        readings = []
        labels = []

        with open(file_path, newline="") as file:
            reader = csv.DictReader(file, delimiter=";")

            for row in reader:
                sensor_values = [
                    float(row[name]) for name in FEATURES
                ]

                label = int(float(row["anomaly"]))

                readings.append(sensor_values)
                labels.append(label)

        # Features are created separately for each CSV file.
        # This prevents history from one file carrying into another.
        temporal_data = create_temporal_features(
            np.array(readings, dtype=float)
        )

        if is_training:
            X_train.extend(temporal_data)
            y_train.extend(labels)
        else:
            X_test.extend(temporal_data)
            y_test.extend(labels)

    X_train = np.array(X_train, dtype=float)
    y_train = np.array(y_train, dtype=int)

    X_test = np.array(X_test, dtype=float)
    y_test = np.array(y_test, dtype=int)

    print("\nTraining records:", len(X_train))
    print("Testing records:", len(X_test))
    print("Features per record:", X_train.shape[1])
    print("Training anomalies:", int(y_train.sum()))
    print("Testing anomalies:", int(y_test.sum()))

    forest = train_random_forest(X_train, y_train)

    predictions = predict_forest(forest, X_test)

    tp = int(np.sum((predictions == 1) & (y_test == 1)))
    fp = int(np.sum((predictions == 1) & (y_test == 0)))
    fn = int(np.sum((predictions == 0) & (y_test == 1)))
    tn = int(np.sum((predictions == 0) & (y_test == 0)))

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    accuracy = (tp + tn) / len(y_test)

    print("\n========== TEMPORAL RANDOM FOREST RESULTS ==========")
    print("True Positives :", tp)
    print("False Positives:", fp)
    print("False Negatives:", fn)
    print("True Negatives :", tn)

    print("\nPrecision:", round(precision, 4))
    print("Recall   :", round(recall, 4))
    print("F1 Score :", round(f1, 4))
    print("Accuracy :", round(accuracy, 4))

    MODEL_FOLDER.mkdir(exist_ok=True)

    model_path = MODEL_FOLDER / "random_forest_temporal_experiment.pkl"

    with open(model_path, "wb") as file:
        pickle.dump(forest, file)

    print("\nExperimental model saved successfully!")
    print("Location:", model_path)


if __name__ == "__main__":
    main()
