
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "ai4i2020.csv"

with open(DATA_FILE, "r", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)
    rows = list(reader)

print("\n========== AI4I DATASET INSPECTION ==========")

print("\nTotal records:", len(rows))

print("\nColumns:")
for column in reader.fieldnames:
    print("-", column)

print("\nMachine failure distribution:")

failure_count = sum(
    int(row["Machine failure"]) == 1
    for row in rows
)

normal_count = len(rows) - failure_count

print("Normal records:", normal_count)
print("Failure records:", failure_count)

print("\nFirst 3 records:")
for row in rows[:3]:
    print(row)

print("\nAI4I inspection completed.")
