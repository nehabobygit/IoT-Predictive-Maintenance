import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sensor_readings.db"

NEW_COLUMNS = {
    "event_id": "TEXT",
    "units_json": "TEXT NOT NULL DEFAULT '{}'",
    "synthetic_fields_json": "TEXT NOT NULL DEFAULT '[]'",
    "source_channels_json": "TEXT NOT NULL DEFAULT '{}'",
}


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
    backup_path = DB_PATH.with_name(
        f"{DB_PATH.stem}.before_prediction_metadata_v2_{timestamp}{DB_PATH.suffix}.bak"
    )
    shutil.copy2(DB_PATH, backup_path)
    print("Database backup created:")
    print(backup_path)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='predictions'"
            ).fetchone()
            if not table_exists:
                raise RuntimeError("The predictions table does not exist.")

            existing = {
                row[1] for row in conn.execute("PRAGMA table_info(predictions)")
            }

            added = []
            for column, definition in NEW_COLUMNS.items():
                if column not in existing:
                    conn.execute(
                        f"ALTER TABLE predictions ADD COLUMN {column} {definition}"
                    )
                    added.append(column)

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_event_id "
                "ON predictions(event_id)"
            )
            conn.commit()

            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {integrity}")

            print("Migration completed.")
            print("Added predictions columns:", added if added else "None; already present")
            print("Prediction records preserved:", count)
            print("SQLite integrity check:", integrity)

    except Exception:
        shutil.copy2(backup_path, DB_PATH)
        print("Migration failed. Database restored from backup.")
        raise


if __name__ == "__main__":
    main()
