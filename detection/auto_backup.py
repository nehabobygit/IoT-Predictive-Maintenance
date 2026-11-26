"""Create verified SQLite snapshots and restore to an exclusive destination."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import time

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = Path(os.getenv("IOT_DB_PATH", BASE_DIR / "data" / "sensor_readings.db"))
BACKUP_DIR = DATABASE.parent / "backups"
BACKUP_INTERVAL = 24 * 60 * 60
MAX_BACKUPS = 7


def copy_verified(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or destination == source:
        raise ValueError("Select an existing source and a separate destination.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(destination)) as copied:
                original.backup(copied)
                if copied.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("SQLite integrity check failed.")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def create_backup(database=DATABASE, backup_dir=BACKUP_DIR):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = Path(backup_dir)
    result = copy_verified(database, backup_dir / f"sensor_readings_{stamp}.db")
    backups = sorted(backup_dir.glob("sensor_readings_????????_??????_??????.db"), reverse=True)
    for old in backups[MAX_BACKUPS:]:
        old.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--once", action="store_true")
    actions.add_argument("--restore", nargs=2, metavar=("BACKUP", "NEW_DATABASE"))
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    if args.restore:
        source, target = map(Path, args.restore)
        if target.resolve() == args.database.resolve():
            parser.error("Restore into a separate database path.")
        print("Restored:", copy_verified(source, target))
        return
    while True:
        print("Backup:", create_backup(args.database, args.backup_dir or args.database.parent / "backups"),
              flush=True)
        if args.once:
            return
        time.sleep(BACKUP_INTERVAL)


if __name__ == "__main__":
    main()
