
import csv
import pickle
import random
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "ai4i2020.csv"
MODEL_FOLDER = BASE_DIR / "models"


def load_data():
    X, y = [], []

    with open(DATA_FILE, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            air = float(row["Air temperature [K]"])
            process = float(row["Process temperature [K]"])
            speed = float(row["Rotational speed [rpm]"])
            torque = float(row["Torque [Nm]"])
            wear = float(row["Tool wear [min]"])

            machine_type = row["Type"]

            type_l = 1 if machine_type == "L" else 0
            type_m = 1 if machine_type == "M" else 0
            type_h = 1 if machine_type == "H" else 0

            X.append([
                air,
                process,
                speed,
                torque,
                wear,
                type_l,
                type_m,
                type_h,
                process - air,
                torque * speed / 1000
            ])

            y.append(int(row["Machine failure"]))

    return np.array(X, dtype=float), np.array(y, dtype=int)


def split_data(y):
    random.seed(42)

    normal = [i for i in range(len(y)) if y[i] == 0]
    failure = [i for i in range(len(y)) if y[i] == 1]

    random.shuffle(normal)
    random.shuffle(failure)

    def split_group(indices):
        a = int(len(indices) * 0.70)
        b = int(len(indices) * 0.85)
        return indices[:a], indices[a:b], indices[b:]

    n_train, n_val, n_test = split_group(normal)
    f_train, f_val, f_test = split_group(failure)

    train = n_train + f_train
    val = n_val + f_val
    test = n_test + f_test

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


def gini(labels):
    if len(labels) == 0:
        return 0

    p = np.mean(labels)
    return 1 - p * p - (1 - p) * (1 - p)


def build_tree(X, y, depth, max_depth, rng):
    positives = int(np.sum(y))
    negatives = len(y) - positives

    node = {
        "prediction": 1 if positives > negatives else 0,
        "feature": None,
        "threshold": None,
        "left": None,
        "right": None
    }

    if (
        depth >= max_depth
        or len(y) < 20
        or positives == 0
        or negatives == 0
    ):
        return node

    feature_count = X.shape[1]
    selected_features = rng.sample(
        range(feature_count),
        max(1, int(np.sqrt(feature_count)))
    )

    best_score = float("inf")
    best_feature = None
    best_threshold = None

    for feature in selected_features:
        values = np.unique(X[:, feature])

        if len(values) < 2:
            continue

        if len(values) > 12:
            positions = np.linspace(
                1, len(values) - 1, 12, dtype=int
            )
            thresholds = [
                (values[i - 1] + values[i]) / 2
                for i in positions
            ]
        else:
            thresholds = [
                (values[i - 1] + values[i]) / 2
                for i in range(1, len(values))
            ]

        for threshold in thresholds:
            left_mask = X[:, feature] <= threshold
            right_mask = ~left_mask

            left_count = int(np.sum(left_mask))
            right_count = int(np.sum(right_mask))

            if left_count < 10 or right_count < 10:
                continue

            score = (
                left_count * gini(y[left_mask])
                + right_count * gini(y[right_mask])
            ) / len(y)

            if score < best_score:
                best_score = score
                best_feature = feature
                best_threshold = float(threshold)

    if best_feature is None:
        return node

    left_mask = X[:, best_feature] <= best_threshold
    right_mask = ~left_mask

    node["feature"] = best_feature
    node["threshold"] = best_threshold

    node["left"] = build_tree(
        X[left_mask], y[left_mask], depth + 1, max_depth, rng
    )

    node["right"] = build_tree(
        X[right_mask], y[right_mask], depth + 1, max_depth, rng
    )

    return node


def predict_tree(tree, row):
    node = tree

    while node["feature"] is not None:
        if row[node["feature"]] <= node["threshold"]:
            node = node["left"]
        else:
            node = node["right"]

    return node["prediction"]


def predict_forest(forest, X):
    predictions = []

    for row in X:
        votes = sum(predict_tree(tree, row) for tree in forest)
        predictions.append(votes / len(forest))

    return np.array(predictions)


def calculate_metrics(actual, predicted):
    tp = int(np.sum((actual == 1) & (predicted == 1)))
    fp = int(np.sum((actual == 0) & (predicted == 1)))
    fn = int(np.sum((actual == 1) & (predicted == 0)))
    tn = int(np.sum((actual == 0) & (predicted == 0)))

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    accuracy = (tp + tn) / len(actual)

    return tp, fp, fn, tn, precision, recall, f1, accuracy


def main():
    MODEL_FOLDER.mkdir(exist_ok=True)

    X, y = load_data()
    train_idx, val_idx, test_idx = split_data(y)

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    print("\n========== AI4I RANDOM FOREST TRAINING ==========")
    print("Training records:", len(y_train))
    print("Validation records:", len(y_val))
    print("Testing records:", len(y_test))
    print("Training failures:", int(np.sum(y_train)))
    print("Validation failures:", int(np.sum(y_val)))
    print("Testing failures:", int(np.sum(y_test)))

    # Oversample failure records in the training set only.
    normal_idx = [i for i in range(len(y_train)) if y_train[i] == 0]
    failure_idx = [i for i in range(len(y_train)) if y_train[i] == 1]

    rng = random.Random(42)

    balanced_idx = normal_idx + rng.choices(
        failure_idx,
        k=len(normal_idx)
    )

    rng.shuffle(balanced_idx)

    X_balanced = X_train[balanced_idx]
    y_balanced = y_train[balanced_idx]

    print("\nBalanced training records:", len(y_balanced))

    forest = []
    tree_count = 25

    for tree_number in range(tree_count):
        sample_indices = [
            rng.randrange(len(y_balanced))
            for _ in range(len(y_balanced))
        ]

        tree = build_tree(
            X_balanced[sample_indices],
            y_balanced[sample_indices],
            depth=0,
            max_depth=8,
            rng=rng
        )

        forest.append(tree)

        if (tree_number + 1) % 5 == 0:
            print("Trees trained:", tree_number + 1)

    val_scores = predict_forest(forest, X_val)

    best_threshold = 0.5
    best_f1 = -1

    for threshold in np.arange(0.05, 0.96, 0.01):
        predictions = (val_scores >= threshold).astype(int)
        metrics = calculate_metrics(y_val, predictions)

        if metrics[6] > best_f1:
            best_f1 = metrics[6]
            best_threshold = float(threshold)

    test_scores = predict_forest(forest, X_test)
    test_predictions = (test_scores >= best_threshold).astype(int)

    results = calculate_metrics(y_test, test_predictions)

    print("\n========== RANDOM FOREST TEST RESULTS ==========")
    print("Selected threshold:", round(best_threshold, 3))
    print("True Positives:", results[0])
    print("False Positives:", results[1])
    print("False Negatives:", results[2])
    print("True Negatives:", results[3])
    print("Precision:", round(results[4], 4))
    print("Recall:", round(results[5], 4))
    print("F1 Score:", round(results[6], 4))
    print("Accuracy:", round(results[7], 4))

    model = {
        "model_type": "random_forest",
        "trees": forest,
        "threshold": best_threshold,
        "features": [
            "air_temperature",
            "process_temperature",
            "rotational_speed",
            "torque",
            "tool_wear",
            "type_L",
            "type_M",
            "type_H",
            "temperature_difference",
            "torque_speed"
        ]
    }

    model_path = MODEL_FOLDER / "ai4i_random_forest.pkl"

    with open(model_path, "wb") as file:
        pickle.dump(model, file)

    print("\nModel saved:", model_path)
    print("Random Forest training completed.")


if __name__ == "__main__":
    main()
