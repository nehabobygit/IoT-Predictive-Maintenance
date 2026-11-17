
import json
import pickle
import sys
from pathlib import Path

import numpy as np

# Import the existing data loading, splitting and prediction functions.
from train_ai4i_rf import load_data, split_data, predict_forest, calculate_metrics


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "models" / "ai4i_random_forest.pkl"
RESULT_FOLDER = BASE_DIR / "results"
RESULT_FILE = RESULT_FOLDER / "ai4i_metrics.json"


def main():
    print("\n========== AI4I MODEL EVALUATION ==========")

    # Check that the trained model exists.
    if not MODEL_FILE.exists():
        print("ERROR: Saved model not found:", MODEL_FILE)
        sys.exit(1)

    # Load the original dataset.
    X, y = load_data()

    # Recreate the exact same stratified split used during training.
    train_idx, val_idx, test_idx = split_data(y)

    X_test = X[test_idx]
    y_test = y[test_idx]

    # Load the already-trained Random Forest.
    with open(MODEL_FILE, "rb") as file:
        model = pickle.load(file)

    if model.get("model_type") != "random_forest":
        print("ERROR: Unexpected model type.")
        sys.exit(1)

    threshold = float(model["threshold"])
    forest = model["trees"]

    # Verify that the model has the expected number of features.
    if len(model["features"]) != X_test.shape[1]:
        print("ERROR: Model and dataset feature counts do not match.")
        sys.exit(1)

    # Evaluate only the held-out test records.
    scores = predict_forest(forest, X_test)
    predictions = (scores >= threshold).astype(int)

    metrics = calculate_metrics(y_test, predictions)

    tp, fp, fn, tn = metrics[:4]
    precision, recall, f1, accuracy = metrics[4:]

    print("\nDataset records:", len(y))
    print("Training records:", len(train_idx))
    print("Validation records:", len(val_idx))
    print("Held-out test records:", len(test_idx))

    print("\nModel:", model["model_type"])
    print("Number of trees:", len(forest))
    print("Decision threshold:", round(threshold, 3))

    print("\n========== CONFUSION MATRIX ==========")
    print("True Positives :", tp)
    print("False Positives:", fp)
    print("False Negatives:", fn)
    print("True Negatives :", tn)

    print("\n========== TEST METRICS ==========")
    print("Accuracy :", round(accuracy, 4))
    print("Precision:", round(precision, 4))
    print("Recall   :", round(recall, 4))
    print("F1 Score :", round(f1, 4))

    # Save reproducible evaluation results.
    RESULT_FOLDER.mkdir(exist_ok=True)

    results = {
        "dataset": "AI4I 2020 Predictive Maintenance Dataset",
        "evaluation": "Held-out test set",
        "total_records": int(len(y)),
        "training_records": int(len(train_idx)),
        "validation_records": int(len(val_idx)),
        "test_records": int(len(test_idx)),
        "test_failures": int(np.sum(y_test)),
        "test_normal": int(len(y_test) - np.sum(y_test)),
        "model_type": model["model_type"],
        "number_of_trees": int(len(forest)),
        "decision_threshold": threshold,
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn
        },
        "metrics": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1)
        }
    }

    with open(RESULT_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print("\nResults saved:", RESULT_FILE)
    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    main()
