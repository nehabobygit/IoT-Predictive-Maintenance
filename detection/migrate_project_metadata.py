"""Safely add metadata columns to the predictive-maintenance SQLite database.

This migration is additive: existing readings, alerts, and predictions are kept.
Historical rows receive explicit legacy markers instead of invented asset IDs.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sensor_readings.db"

COLUMN_DEFINITIONS = {
    "sensor_readings": {
        "asset_id": "TEXT NOT NULL DEFAULT 'LEGACY-UNKNOWN'",
        "source": "TEXT NOT NULL DEFAULT 'legacy_unknown'",
        "schema_version": "TEXT NOT NULL DEFAULT 'legacy'",
        "event_id": "TEXT",
        "run_id": "TEXT",
        "source_timestamp": "TEXT",
        "units_json": "TEXT NOT NULL DEFAULT '{}'",
        "synthetic_fields_json": "TEXT NOT NULL DEFAULT '[]'",
        "source_channels_json": "TEXT NOT NULL DEFAULT '{}'",
        "actual_anomaly": "INTEGER",
    },
    "alerts": {
        "asset_id": "TEXT NOT NULL DEFAULT 'LEGACY-UNKNOWN'",
        "source": "TEXT NOT NULL DEFAULT 'legacy_unknown'",
        "schema_version": "TEXT NOT NULL DEFAULT 'legacy'",
        "event_id": "TEXT",
        "run_id": "TEXT",
        "unit": "TEXT",
    },
    "predictions": {
        "run_id": "TEXT",
        "asset_id": "TEXT",
        "source": "TEXT NOT NULL DEFAULT 'legacy_unknown'",
        "schema_version": "TEXT NOT NULL DEFAULT 'legacy'",
        "source_timestamp": "TEXT",
    },
}


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_sensor_readings_asset_source_id "
    "ON sensor_readings(asset_id, source, id)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_asset_source_id "
    "ON alerts(asset_id, source, id)",
    "CREATE INDEX IF NOT EXISTS idx_predictions_run_id_id "
    "ON predictions(run_id, id)",
]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
    backup_path = DB_PATH.with_name(
        f"{DB_PATH.stem}.before_metadata_{timestamp}.bak"
    )

    # Use SQLite's backup API so the backup is consistent even if WAL is enabled.
    with sqlite3.connect(DB_PATH) as source_conn:
        with sqlite3.connect(backup_path) as backup_conn:
            source_conn.backup(backup_conn)

    print("Database backup created:")
    print(backup_path)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")

        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        required_tables = set(COLUMN_DEFINITIONS)
        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Required database tables are missing: "
                + ", ".join(sorted(missing_tables))
            )

        changes = []

        for table, definitions in COLUMN_DEFINITIONS.items():
            existing_columns = {
                row[1] for row in conn.execute(f"PRAGMA table_info({table})")
            }

            for column, definition in definitions.items():
                if column not in existing_columns:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )
                    changes.append(f"Added {table}.{column}")

        for statement in INDEX_STATEMENTS:
            conn.execute(statement)

        conn.commit()

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")

        print("\nMigration completed.")
        if changes:
            for change in changes:
                print("-", change)
        else:
            print("- No columns needed to be added; schema was already current.")

        print("\nExisting record counts:")
        for table in COLUMN_DEFINITIONS:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"- {table}: {count}")

        print("\nSQLite integrity check:", integrity)


if __name__ == "__main__":
    main()
