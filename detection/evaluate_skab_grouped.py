"""Tune on valve1 and score disjoint SKAB groups using causal detectors."""
import csv
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

from detection.sequence_metrics import aggregate, score_sequence

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "SKAB-master" / "data"
RESULTS = ROOT / "results"
FIELDS = ("Accelerometer1RMS", "Temperature", "Current", "Pressure")
UNITS = ("g", "deg C", "A", "bar")
WARMUP = 60
PARAMETERS = [(limit, persistence) for limit in (3, 4, 5, 6, 8, 10) for persistence in (1, 3, 5)]


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream, delimiter=";"))
    return (
        np.array([[float(r[f]) for f in FIELDS] for r in records]),
        np.array([int(float(r["anomaly"])) for r in records]),
        [datetime.fromisoformat(r["datetime"]) for r in records],
        [r["changepoint"] for r in records],
    )


def rolling(values):
    windows = np.lib.stride_tricks.sliding_window_view(values, 11, axis=0)
    previous = windows[:, :, :10]
    difference = np.abs(windows[:, :, 10] - previous.mean(axis=2))
    spread = previous.std(axis=2, ddof=1)
    scores = np.divide(difference, spread, out=np.zeros_like(difference), where=spread > 0)
    return np.r_[np.zeros(10, dtype=bool), (scores > 1.5).any(axis=1)]


def reference(values, limit, persistence):
    baseline = values[:WARMUP]
    median = np.median(baseline, axis=0)
    scale = np.maximum(np.median(np.abs(baseline - median), axis=0)*1.4826,
                       np.maximum(baseline.std(axis=0)*.25, 1e-6))
    score = np.max(np.abs(values - median) / scale, axis=1)
    exceeds = score > limit
    exceeds[:WARMUP] = False
    return np.convolve(exceeds.astype(int), np.ones(persistence, dtype=int), "full")[:len(values)] == persistence


def score(record, detector):
    values, actual, times, _ = record
    return score_sequence(actual[WARMUP:], detector(values)[WARMUP:], times[WARMUP:])


def main():
    validation_paths = sorted((DATA / "valve1").glob("*.csv"))
    test_paths = sorted((DATA / "valve2").glob("*.csv")) + sorted((DATA / "other").glob("*.csv"))
    validation = [read(path) for path in validation_paths]
    tuning = {}
    for limit, persistence in PARAMETERS:
        tuning[(limit, persistence)] = aggregate(
            [score(row, lambda values: reference(values, limit, persistence)) for row in validation]
        )["metrics"]
    limit, persistence = max(tuning, key=lambda key: (tuning[key]["f1_score"],
                                                    -tuning[key]["false_positive_rate"]))
    selected = lambda values: reference(values, limit, persistence)
    records = [read(path) for path in test_paths]
    ids = [p.relative_to(DATA).as_posix() for p in test_paths]
    baseline_rows = [score(record, rolling) for record in records]
    test_rows = [score(record, selected) for record in records]
    report = {
        "dataset": "SKAB valve2 and other groups",
        "model_type": "Robust reference with persistence",
        "evaluation": "Whole valve1 sequences for selection, other groups held out for this protocol",
        "parameters": {"threshold": limit, "consecutive_samples": persistence, "warmup": WARMUP},
        "validation_metrics": tuning[(limit, persistence)],
        "validation_sequences": [p.relative_to(DATA).as_posix() for p in validation_paths],
        "test_sequences": {key: hashlib.sha256(path.read_bytes()).hexdigest()
                           for key, path in zip(ids, test_paths)},
        "units": dict(zip(FIELDS, UNITS)), "baseline": aggregate(baseline_rows),
        "per_sequence": {key: {"selected": aggregate([row]), "rolling_z": aggregate([baseline]),
                               "missed_episodes": row["missed_episodes"],
                               "detection_delays_seconds": row["delays_seconds"]}
                         for key, row, baseline in zip(ids, test_rows, baseline_rows)},
        "limitations": ["Prior project experiments inspected both final groups. They are disjoint in this run, but are not a novel external dataset.",
                        "The first 60 observations initialize a causal reference and are excluded from both scores.",
                        "Per-shift false alarm counts are extrapolated from the observed recorded duration."],
        **aggregate(test_rows),
    }
    with (RESULTS / "skab_grouped_metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    with (RESULTS / "skab_grouped_fixture.csv.gz").open("wb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(["sequence", "source_timestamp", "anomaly", "changepoint",
                                 *(f"{field} [{unit}]" for field, unit in zip(FIELDS, UNITS))])
                for name, (values, actual, times, points) in zip(ids, records):
                    writer.writerows((name, t.isoformat(sep=" "), label, point, *samples)
                                     for samples, label, t, point in zip(values, actual, times, points))
    print(json.dumps({k: report[k] for k in ("parameters", "metrics", "confusion_matrix", "baseline",
                                           "episodes_detected", "episodes_missed", "false_alarm_episodes_per_8_hours",
                                           "detection_delay_seconds_median")}, indent=2))


if __name__ == "__main__":
    main()
