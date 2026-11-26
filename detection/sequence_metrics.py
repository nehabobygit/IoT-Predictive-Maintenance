"""Point and episode scoring without joining independent data sequences."""
from datetime import datetime

import numpy as np

from detection.train_ai4i_rf import calculate_metrics


def episode_starts(mask):
    return np.flatnonzero(mask & ~np.r_[False, mask[:-1]]) if len(mask) else []


def score_sequence(actual, predicted, times):
    actual, predicted = np.asarray(actual, dtype=bool), np.asarray(predicted, dtype=bool)
    tp, fp, fn, tn, _, _, _, _ = calculate_metrics(actual, predicted)
    delays, missed = [], []
    for start in episode_starts(actual):
        end = start
        while end < len(actual) and actual[end]:
            end += 1
        detections = np.flatnonzero(predicted[start:end])
        if len(detections):
            first = int(start + detections[0])
            delays.append((times[first] - times[start]).total_seconds())
        else:
            missed.append({"start": times[start].isoformat(), "samples": int(end - start)})
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "delays_seconds": delays,
            "false_alarm_episodes": len(episode_starts(predicted & ~actual)),
            "missed_episodes": missed, "seconds": max(0, (times[-1] - times[0]).total_seconds())}


def aggregate(results):
    counts = {key: sum(row[key] for row in results) for key in ("tp", "fp", "fn", "tn")}
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    delays = [delay for row in results for delay in row["delays_seconds"]]
    false_alarms = sum(row["false_alarm_episodes"] for row in results)
    duration = sum(row["seconds"] for row in results)
    return {
        "metrics": {"accuracy": (tp + tn) / max(tp + fp + fn + tn, 1),
                    "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1),
                    "f1_score": 2*tp / max(2*tp+fp+fn, 1), "false_positive_rate": fp / max(fp+tn, 1)},
        "confusion_matrix": {"true_positives": tp, "false_positives": fp,
                             "false_negatives": fn, "true_negatives": tn},
        "test_records": tp + fp + fn + tn, "test_failures": tp + fn,
        "episodes_detected": len(delays),
        "episodes_missed": sum(len(row["missed_episodes"]) for row in results),
        "detection_delay_seconds_median": float(np.median(delays)) if delays else None,
        "false_alarm_episodes": false_alarms, "observed_hours": duration / 3600,
        "false_alarm_episodes_per_8_hours": false_alarms * 28800 / duration if duration else None,
    }
