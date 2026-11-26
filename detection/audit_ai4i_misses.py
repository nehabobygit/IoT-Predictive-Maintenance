"""Audit missed AI4I failures on the documented holdout."""
from collections import Counter
import csv
import json
import pickle

import numpy as np

from detection.train_ai4i_improved import ROOT, evaluate, physical_features
from detection.train_ai4i_rf import load_data, predict_forest, split_data
from messaging.model_security import verify_ai4i_model


def main():
    values, labels = load_data()
    ids = np.array(split_data(labels)[2])
    with (ROOT / "data" / "ai4i2020.csv").open(newline="", encoding="utf-8-sig") as stream:
        records = list(csv.DictReader(stream))
    y = labels[ids]
    outcomes = {"always_normal": evaluate(y, np.zeros(len(y)), 1.0)}
    missed = {}
    for name, filename, features in (
        ("original", "ai4i_random_forest.pkl", values),
        ("improved", "ai4i_improved.pkl", physical_features(values)),
    ):
        path = ROOT / "models" / filename
        verify_ai4i_model(path, expected_default=True)
        with path.open("rb") as stream:
            model = pickle.load(stream)
        scores = predict_forest(model["trees"], features[ids])
        outcomes[name] = evaluate(y, scores, model["threshold"])
        outcomes[name]["metrics"]["false_negative_rate"] = 1-outcomes[name]["metrics"]["recall"]
        misses = []
        for i in np.flatnonzero((y == 1) & (scores < model["threshold"])):
            row = records[int(ids[i])]
            flags = [flag for flag in ("TWF", "HDF", "PWF", "OSF", "RNF") if row[flag] == "1"]
            misses.append({"udi": int(row["UDI"]), "product_type": row["Type"], "flags": flags,
                           "score": float(scores[i])})
        missed[name] = misses
    report = {"outcomes": outcomes, "missed_records": missed,
              "original_misses_recovered": sorted(set(r["udi"] for r in missed["original"]) -
                                                  set(r["udi"] for r in missed["improved"])),
              "missed_by_flag": {name: dict(Counter(flag for row in rows for flag in row["flags"] or ["none"]))
                                 for name, rows in missed.items()}}
    (ROOT / "results" / "ai4i_miss_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"missed_by_flag": report["missed_by_flag"],
                      "original_misses_recovered": len(report["original_misses_recovered"])}, indent=2))


if __name__ == "__main__":
    main()
