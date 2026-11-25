
import sqlite3
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "data" / "sensor_readings.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"

BACKUP_INTERVAL = 24 * 60 * 60
MAX_BACKUPS = 7


def create_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if not DATABASE.exists():
        print("Database not found.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_file = BACKUP_DIR / f"sensor_readings_{timestamp}.db"

    try:
        with sqlite3.connect(str(DATABASE)) as source:
            with sqlite3.connect(str(backup_file)) as destination:
                source.backup(destination)

        with sqlite3.connect(str(backup_file)) as connection:
            result = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

        if result != "ok":
            raise RuntimeError("Backup integrity check failed")

        print(f"Backup successful: {backup_file.name}")

        # Keep only the latest seven automatic backups.
        backups = sorted(
            BACKUP_DIR.glob("sensor_readings_????????_??????_??????.db"),
            key=lambda file: file.name,
            reverse=True
        )

        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()
            print(f"Removed old automatic backup: {old_backup.name}")

    except Exception as error:
        backup_file.unlink(missing_ok=True)
        print(f"Backup failed: {error}")


if __name__ == "__main__":
    print("Automatic database backup service started.")

    while True:
        create_backup()
        time.sleep(BACKUP_INTERVAL)
