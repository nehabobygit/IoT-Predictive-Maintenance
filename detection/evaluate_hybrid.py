
import json
import sqlite3
import statistics
from pathlib import Path

from detection.hybrid_detector import detect_hybrid

BASE_DIR = Path(__file__).resolve().parent.parent
DB = BASE_DIR / "data" / "sensor_readings.db"
RESULT_FILE = BASE_DIR / "results" / "hybrid_evaluation.json"

SENSORS = ["temperature", "vibration", "humidity", "pressure", "current"]
WINDOW = 10

DEVELOPMENT_RUN = "6bb6fc17-5df6-466a-a13e-d7d6b4c87eb3"
TEST_RUN = "78d0f37d-40fa-47ba-aabe-a39802c766a5"

SUPPLEMENTARY_RUNS = [
    "bbbe28c6-fbee-4b41-a691-e831fda135be",
    "da77133d-66a6-4616-b511-0ff7d150fe00",
    "6076b72c-6be2-4d20-8d7c-01bafbc9daf4",
    "932af96f-756a-4e9a-b11e-bcbd96d574a9",
    "e572f7bb-20e9-49d8-993e-59ffbbf84966",
]


def z_score(history, value):
    previous = history[-WINDOW:]

    if len(previous) < 5:
        return None

    std = statistics.stdev(previous)

    if std == 0:
        return None

    return (value - statistics.mean(previous)) / std


def baseline(history, values):
    return any(
        (z := z_score(history[s], values[s])) is not None
        and abs(z) > 1.5
        for s in SENSORS
    )


def hybrid(history, values):
    return bool(detect_hybrid(history, values))


def evaluate(rows, detector):
    history = {s: [] for s in SENSORS}
    tp = fp = fn = tn = 0

    for row in rows:
        values = dict(zip(SENSORS, row[:5]))
        actual = int(row[5])

        predicted = detector(history, values)

        for sensor in SENSORS:
            history[sensor].append(values[sensor])

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def main():
    results = {
        "evaluation_type": "simulated_sensor_anomaly_detection",
        "split_method": "fixed_run_ids",
        "notes": (
            "Run IDs are fixed to prevent automatic reassignment. "
            "This does not independently establish that the test run "
            "was excluded from earlier detector tuning. "
            "The hybrid evaluation imports the current production "
            "detector, including gradual temperature-rise and "
            "sustained humidity-drift rules."
        ),
        "runs": [],
    }

    selected_runs = [
        ("DEVELOPMENT", DEVELOPMENT_RUN),
        ("TEST", TEST_RUN),
    ] + [
        ("SUPPLEMENTARY", run_id)
        for run_id in SUPPLEMENTARY_RUNS
    ]

    with sqlite3.connect(DB) as conn:
        for role, run_id in selected_runs:
            rows = conn.execute(
                """
                SELECT temperature, vibration, humidity,
                       pressure, current, actual_anomaly
                FROM sensor_readings
                WHERE source = 'simulated_sensor'
                  AND run_id = ?
                  AND actual_anomaly IN (0, 1)
                ORDER BY id
                """,
                (run_id,),
            ).fetchall()

            if not rows:
                raise ValueError(
                    f"No labelled readings found for {role}: {run_id}"
                )

            print(f"\n{role} | {len(rows)} readings")

            run_result = {
                "role": role,
                "run_id": run_id,
                "readings": len(rows),
            }

            for name, detector in [
                ("BASELINE", baseline),
                ("HYBRID", hybrid),
            ]:
                metrics = evaluate(rows, detector)
                run_result[name.lower()] = metrics

                print(
                    f"{name}: "
                    f"TP={metrics['tp']} "
                    f"FP={metrics['fp']} "
                    f"FN={metrics['fn']} "
                    f"TN={metrics['tn']} "
                    f"Precision={metrics['precision']:.4f} "
                    f"Recall={metrics['recall']:.4f} "
                    f"F1={metrics['f1']:.4f}"
                )

            results["runs"].append(run_result)

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    RESULT_FILE.write_text(
        json.dumps(results, indent=4),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {RESULT_FILE}")
    print("Evaluation completed. Live system unchanged.")


if __name__ == "__main__":
    main()
