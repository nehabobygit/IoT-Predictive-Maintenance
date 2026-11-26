"""Train AI4I classifiers and export the selected NumPy-compatible forest."""
import csv
import json
import pickle
from pathlib import Path

import numpy as np

from detection.train_ai4i_rf import calculate_metrics, load_data, predict_forest, split_data

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FEATURES = [
    "air_temperature", "process_temperature", "rotational_speed", "torque",
    "tool_wear", "type_L", "type_M", "type_H", "temperature_difference", "torque_speed",
]
FEATURES = LEGACY_FEATURES + ["wear_torque"]


def physical_features(rows):
    rows = np.asarray(rows)
    return np.column_stack((rows, rows[:, 3] * rows[:, 4]))


def operating_features(air, process, speed, torque, wear, machine_type):
    return [air, process, speed, torque, wear, machine_type == "L",
            machine_type == "M", machine_type == "H", process - air, torque * speed / 1000]


def build_tree(X, y, weights, rng, depth, max_depth, min_leaf, feature_count):
    total = weights.sum()
    positive = np.dot(y, weights)
    node = {"prediction": float(positive / total), "feature": None}
    if depth == max_depth or len(y) < 2 * min_leaf or positive == 0 or positive == total:
        return node

    best_loss = positive * (1 - positive / total)
    best_split = None
    for feature in rng.choice(X.shape[1], feature_count, replace=False):
        order = np.argsort(X[:, feature], kind="stable")
        sorted_x = X[order, feature]
        cuts = np.flatnonzero(sorted_x[:-1] < sorted_x[1:])
        cuts = cuts[(cuts >= min_leaf - 1) & (cuts < len(y) - min_leaf)]
        if not cuts.size:
            continue
        left_weight = np.cumsum(weights[order])[cuts]
        left_positive = np.cumsum(y[order] * weights[order])[cuts]
        right_weight = total - left_weight
        right_positive = positive - left_positive
        losses = left_positive * (1 - left_positive / left_weight)
        losses += right_positive * (1 - right_positive / right_weight)
        index = np.argmin(losses)
        if losses[index] < best_loss - 1e-10:
            best_loss = losses[index]
            cut = cuts[index]
            best_split = (int(feature), float((sorted_x[cut] + sorted_x[cut + 1]) / 2))

    if best_split is None:
        return node
    feature, threshold = best_split
    left = X[:, feature] <= threshold
    children = [
        build_tree(X[mask], y[mask], weights[mask], rng, depth + 1,
                   max_depth, min_leaf, feature_count)
        for mask in (left, ~left)
    ]
    return dict(node, feature=feature, threshold=threshold, left=children[0], right=children[1])


def fit(X, y, *, trees, depth, leaf, features, positive_weight):
    rng = np.random.default_rng(42)
    weights = np.where(y == 1, positive_weight, 1.0)
    forest = []
    for _ in range(trees):
        sample = rng.integers(len(y), size=len(y)) if trees > 1 else np.arange(len(y))
        forest.append(build_tree(X[sample], y[sample], weights[sample], rng,
                                 0, depth, leaf, features))
    return forest


def evaluate(y, scores, threshold):
    tp, fp, fn, tn, precision, recall, f1, accuracy = calculate_metrics(y, scores >= threshold)
    order = np.argsort(-scores, kind="stable")
    ends = np.r_[np.flatnonzero(np.diff(scores[order])), len(y) - 1]
    true = np.cumsum(y[order])[ends]
    false = ends + 1 - true
    tpr = np.r_[0, true / true[-1]]
    fpr = np.r_[0, false / false[-1]]
    return {
        "metrics": {"accuracy": accuracy, "precision": precision, "recall": recall,
                    "f1_score": f1, "roc_auc": float(np.trapezoid(tpr, fpr)),
                    "pr_auc": float(np.dot(np.diff(tpr), true / (ends + 1)))},
        "confusion_matrix": {"true_positives": tp, "false_positives": fp,
                             "false_negatives": fn, "true_negatives": tn},
    }


def choose_threshold(y, scores):
    ranked = []
    for threshold in np.unique(scores):
        _, _, _, _, precision, recall, f1, _ = calculate_metrics(y, scores >= threshold)
        ranked.append((f1, recall, precision, float(threshold)))
    return max(ranked)[-1]


CANDIDATES = {
    "Decision tree": dict(trees=1, depth=8, leaf=3, features=11, positive_weight=1),
    "Random forest": dict(trees=64, depth=14, leaf=2, features=8, positive_weight=1),
    "Weighted random forest": dict(trees=64, depth=14, leaf=3, features=9, positive_weight=5),
}


def train(rows, y, split):
    train_ids, validation_ids, _ = split
    reports = []
    models = {}
    for name, settings in CANDIDATES.items():
        forest = fit(rows[train_ids], y[train_ids], **settings)
        scores = predict_forest(forest, rows[validation_ids])
        threshold = choose_threshold(y[validation_ids], scores)
        validation = evaluate(y[validation_ids], scores, threshold)
        reports.append({"name": name, "threshold": threshold, **validation})
        models[name] = forest
        print(name, validation["metrics"], flush=True)
    winner = max(reports, key=lambda result: tuple(
        result["metrics"][metric] for metric in ("f1_score", "recall", "pr_auc")
    ))
    return winner, models[winner["name"]], reports


def main():
    X, y = load_data()
    if not np.isfinite(X).all() or set(np.unique(y)) != {0, 1}:
        raise ValueError("AI4I input contains invalid features or labels")
    rows = physical_features(X)
    split = split_data(y)
    train_ids, validation_ids, test_ids = split
    winner, forest, comparisons = train(rows, y, split)
    threshold = winner["threshold"]
    improved = evaluate(y[test_ids], predict_forest(forest, rows[test_ids]), threshold)

    # The baseline is the repository's original trusted model.
    from messaging.model_security import verify_ai4i_model

    legacy_path = ROOT / "models" / "ai4i_random_forest.pkl"
    verify_ai4i_model(legacy_path, expected_default=True)
    with legacy_path.open("rb") as stream:
        legacy = pickle.load(stream)
    baseline = evaluate(y[test_ids], predict_forest(legacy["trees"], X[test_ids]), legacy["threshold"])

    # AI4I has no physical machine IDs or time-to-failure target. A second
    # experiment tests distribution shift in UDI order with fresh training.
    ordered = tuple(np.arange(start, stop) for start, stop in [(0, 7000), (7000, 8500), (8500, 10000)])
    ordered_winner, ordered_forest, _ = train(rows, y, ordered)
    ordered_test = ordered[2]
    ordered_metrics = evaluate(y[ordered_test], predict_forest(ordered_forest, rows[ordered_test]),
                               ordered_winner["threshold"])

    with (ROOT / "data" / "ai4i2020.csv").open(encoding="utf-8-sig", newline="") as stream:
        labels = list(csv.DictReader(stream))
    audit = {
        "positive_records": int(y.sum()),
        "duplicate_feature_rows": len(X) - len(np.unique(X, axis=0)),
        "missing_feature_values": int(np.count_nonzero(~np.isfinite(X))),
        "failure_without_mode_flag": sum(
            row["Machine failure"] == "1" and not any(
                row[field] == "1" for field in ("TWF", "HDF", "PWF", "OSF", "RNF")
            ) for row in labels
        ),
    }
    report = {
        "dataset": "AI4I 2020 Predictive Maintenance Dataset",
        "evaluation": "Stratified 70/15/15 split shared with the original model",
        "model_type": winner["name"], "decision_threshold": threshold,
        "training_records": len(train_ids), "validation_records": len(validation_ids),
        "test_records": len(test_ids), "test_failures": int(y[test_ids].sum()),
        "audit": audit, "baseline": baseline, "validation_comparison": comparisons,
        "ordered_evaluation": {"model_type": ordered_winner["name"],
                               "test_records": len(ordered_test), **ordered_metrics},
        **improved,
    }
    model = {"model_type": winner["name"], "trees": forest, "threshold": threshold, "features": FEATURES}
    (ROOT / "models" / "ai4i_improved.pkl").write_bytes(pickle.dumps(model, protocol=4))
    (ROOT / "results" / "ai4i_improved_metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
