"""Exercise authorization, data integrity and the portable recovery path."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from werkzeug.security import generate_password_hash

from dashboard import app as dashboard
from detection.auto_backup import copy_verified, create_backup
from messaging import consumer
from messaging.model_security import load_verified_ai4i_model


class ReviewWorkflowTests(unittest.TestCase):
    def test_audit_linkage_role_enforcement_and_backup_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            live = Path(directory) / "live.db"
            with patch.object(consumer, "DB_PATH", live), patch.object(dashboard, "DB_PATH", live):
                consumer.create_database()
                password = generate_password_hash("strong-password")
                with closing(sqlite3.connect(live)) as db, db:
                    dashboard.create_maintenance_tables(db)
                    dashboard.init_accounts(db)
                    db.executemany("INSERT INTO dashboard_users VALUES (?, ?, ?)",
                                   [("operator-a", password, "operator"), ("viewer-v", password, "viewer")])
                    alert = db.execute("""
                        INSERT INTO alerts (asset_id, recommendation, severity)
                        VALUES ('SIM-MOTOR-001', 'Inspect vibration', 'MEDIUM')
                    """).lastrowid
                    # Use a committed telemetry row from the simulation asset.
                    db.execute("""
                        INSERT INTO sensor_readings (asset_id, source, vibration) VALUES
                        ('SIM-MOTOR-001', 'simulated_sensor', 12.5)
                    """)
                with dashboard.app.test_client() as browser:
                    self.assertEqual(browser.get("/healthz").status_code, 200)
                    for who in ("viewer-v", "operator-a"):
                        browser.get("/login")
                        with browser.session_transaction() as session:
                            token = session["auth_csrf"]
                        self.assertEqual(browser.post("/login", data={
                            "username": who, "password": "strong-password", "csrf_token": token
                        }).status_code, 303)
                        self.assertEqual(browser.get("/?page=maintenance").status_code, 200)
                        with browser.session_transaction() as session:
                            csrf = session["maintenance_csrf"]
                        data = {"csrf_token": csrf, "action": "acknowledge", "alert_id": alert,
                                "operator": "fake-user"}
                        expected = 403 if who == "viewer-v" else 303
                        self.assertEqual(browser.post("/maintenance/action", data=data).status_code, expected)
                        if who == "operator-a":
                            self.assertEqual(browser.post("/maintenance/action", data={
                                **data, "csrf_token": "bad",
                            }).status_code, 400)
                            response = browser.post("/maintenance/action", data={
                                **data, "action": "schedule", "assigned_to": "Engineer B", "priority": "MEDIUM",
                                "scheduled_for": "2026-12-01T09:00",
                            })
                            self.assertEqual(response.status_code, 303)
                            with closing(sqlite3.connect(live)) as db:
                                task = db.execute("SELECT id FROM maintenance_tasks").fetchone()[0]
                            for action, values in (
                                ("update", {"assigned_to": "Engineer C", "priority": "HIGH"}),
                                ("complete", {"completion_notes": "Inspected test equipment"}),
                            ):
                                response = browser.post("/maintenance/action", data={
                                    **data, **values, "action": action, "task_id": task,
                                })
                                self.assertEqual(response.status_code, 303)
                            self.assertIn(b"Maintenance Audit History", browser.get("/?page=maintenance").data)
                            audit = browser.get("/api/maintenance/audit").get_json()
                            self.assertEqual({r["actor"] for r in audit}, {"operator-a"})
                        self.assertEqual(browser.post("/logout", data={"csrf_token": csrf}).status_code, 302)

                for _ in range(8):
                    backup = create_backup(live, Path(directory) / "backups")
                self.assertEqual(len(list(backup.parent.glob("*.db"))), 7)
                restored = copy_verified(backup, Path(directory) / "restored.db")
                with self.assertRaises(FileExistsError):
                    copy_verified(backup, live)
                with closing(sqlite3.connect(restored)) as db:
                    self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                    self.assertEqual(db.execute("SELECT asset_id, vibration FROM sensor_readings").fetchone(),
                                     ("SIM-MOTOR-001", 12.5))
                    self.assertEqual(db.execute("""
                        SELECT t.status, t.alert_id, t.asset_id, a.operator
                        FROM maintenance_tasks t JOIN alert_acknowledgements a ON a.alert_id=t.alert_id
                    """).fetchone(), ("COMPLETED", alert, "SIM-MOTOR-001", "operator-a"))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM maintenance_audit").fetchone(), (4,))

    def test_rate_limit_and_malformed_mqtt(self):
        with tempfile.TemporaryDirectory() as directory:
            live = Path(directory) / "test.db"
            with patch.object(dashboard, "DB_PATH", live):
                with closing(sqlite3.connect(live)) as db, db:
                    dashboard.init_accounts(db)
                    db.execute("INSERT INTO dashboard_users VALUES (?, ?, 'admin')",
                               ("admin", generate_password_hash("valid-password")))
                with dashboard.app.test_client() as browser:
                    browser.get("/login")
                    with browser.session_transaction() as session:
                        token = session["auth_csrf"]
                    for _ in range(8):
                        self.assertEqual(browser.post("/login", data={
                            "username": "admin", "password": "no", "csrf_token": token,
                        }).status_code, 200)
                    self.assertEqual(browser.post("/login", data={
                        "username": "admin", "password": "valid-password", "csrf_token": token,
                    }).status_code, 429)
        client = Mock()
        packet = Mock(payload=b"{invalid", topic=consumer.TOPIC, qos=1, mid=12)
        consumer.on_message(client, None, packet)
        client.ack.assert_called_once_with(12, 1)

    def test_artifact_path_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory)
            bad = location / "ai4i_improved.pkl"
            bad.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "integrity"):
                load_verified_ai4i_model(bad, location)
            with self.assertRaisesRegex(ValueError, "directly inside"):
                load_verified_ai4i_model(bad, location / "separate")


if __name__ == "__main__":
    unittest.main()
