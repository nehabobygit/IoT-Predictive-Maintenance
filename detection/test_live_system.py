"""Exercise the live simulation through persistence, forecast and Flask views."""
import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import app as dashboard
from messaging import consumer, publisher
from messaging.message_contract import new_id
from sensors.machine_simulator import EPISODE_LENGTH, MachineSimulator, PROFILES


class LiveSystemTests(unittest.TestCase):
    def test_live_fleet_records_faults_and_warns_before_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "test.db"
            with (
                patch.object(consumer, "DB_PATH", database),
                patch.object(dashboard, "DB_PATH", database),
                patch.object(publisher, "FAULT_LOG", root / "faults.csv"),
                patch.object(publisher, "FAULT_LOG_V2", root / "faults_v2.csv"),
                patch.dict(consumer.last_alert_time, {}, clear=True),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                consumer.create_database()
                with contextlib.closing(sqlite3.connect(database)) as conn:
                    dashboard.create_maintenance_tables(conn)
                    dashboard.init_accounts(conn)
                    run = new_id()
                    machines = {asset: MachineSimulator(asset, seed=1) for asset in PROFILES}
                    truth = {asset: MachineSimulator(asset, seed=1) for asset in PROFILES}
                    first_failure = {}
                    prior_warnings = set()
                    for cycle in range(EPISODE_LENGTH):
                        for asset, simulator in machines.items():
                            event = publisher.generate_readings(run, asset, simulator)
                            _, _, failed = truth[asset].sample()
                            if failed and asset not in first_failure:
                                first_failure[asset] = cycle
                            consumer.process_sensor_message(event)
                            findings = conn.execute("""
                                SELECT sensor, category FROM anomaly_events a
                                JOIN sensor_readings r ON r.id = a.reading_id
                                WHERE r.event_id = ?
                            """, (event["event_id"],)).fetchall()
                            sensors = {sensor for sensor, _ in findings}
                            if cycle < 15:
                                self.assertEqual(sensors, set())
                            if cycle in (15, 27, 31, 48, 50, 89):
                                expected = {15: {"temperature"}, 27: {"temperature"},
                                            31: {"vibration"}, 48: {"pressure"}, 50: {"current"},
                                            89: {"vibration", "current"}}[cycle]
                                self.assertLessEqual(expected, sensors)
                            if cycle == 44:
                                self.assertIn(("humidity", "sensor_drift"), findings)
                            if asset not in first_failure and conn.execute("""
                                SELECT 1 FROM alerts WHERE event_id = ? AND category = 'degradation_forecast'
                            """, (event["event_id"],)).fetchone():
                                prior_warnings.add(asset)

                    self.assertTrue(first_failure)
                    self.assertEqual(prior_warnings & first_failure.keys(), first_failure.keys())
                    count = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
                    self.assertEqual(count, len(PROFILES) * EPISODE_LENGTH)
                    self.assertGreater(conn.execute("SELECT COUNT(*) FROM maintenance_forecasts").fetchone()[0], 0)

                    username, password = "demo_operator", "test-password"
                    with dashboard.app.test_client() as setup:
                        self.assertIn(b"Create an account", setup.get("/login").data)
                        self.assertIn(b"Confirm password", setup.get("/register").data)
                        fields = {"username": username, "password": password, "confirm_password": password}
                        self.assertEqual(setup.post("/register", data=fields).status_code, 400)
                        with setup.session_transaction() as session:
                            fields["csrf_token"] = session["auth_csrf"]
                        mismatch = setup.post("/register", data={**fields, "confirm_password": "different"})
                        self.assertIn(b"The passwords do not match", mismatch.data)
                        created = setup.post("/register", data=fields, follow_redirects=True)
                        self.assertIn(b"Account created. You can now sign in.", created.data)
                        self.assertEqual(setup.get("/api/monitoring").status_code, 401)
                        self.assertEqual(setup.get("/register").status_code, 303)
                        self.assertEqual(setup.post("/register", data=fields).status_code, 303)
                    saved = conn.execute("SELECT username, password_hash FROM dashboard_users").fetchall()
                    self.assertEqual(len(saved), 1)
                    self.assertEqual(saved[0][0], username)
                    self.assertNotEqual(saved[0][1], password)

                    with dashboard.app.test_client() as client:
                        self.assertEqual(client.get("/api/monitoring").status_code, 401)
                        self.assertNotIn(b"Create an account", client.get("/login").data)
                        with client.session_transaction() as session:
                            login = {"username": username, "password": password, "csrf_token": session["auth_csrf"]}
                        bad_login = client.post("/login", data={**login, "password": "wrong"})
                        self.assertIn(b"Invalid username or password.", bad_login.data)
                        response = client.post("/login", data=login)
                        self.assertEqual(response.status_code, 303)
                        fleet = client.get("/api/monitoring").get_json()
                        self.assertEqual(len(fleet["machines"]), len(PROFILES))
                        self.assertEqual(sum(fleet["counts"].values()), len(PROFILES))
                        self.assertGreater(fleet["active_alerts"], 0)
                        for page in ("overview", "sensors", "alerts", "history", "prediction",
                                     "ai4i_replay", "maintenance", "notifications"):
                            response = client.get("/", query_string={"page": page})
                            self.assertEqual(response.status_code, 200, page)
                        alert_page = client.get("/?page=alerts&asset=SIM-MOTOR-001&sensor=pressure")
                        self.assertIn(b"Recent Anomaly Events", alert_page.data)
                        self.assertIn(b"Pressure variation", alert_page.data)
                        reports = client.get("/api/model-performance").get_json()
                        self.assertIn("confusion_matrix", reports["live"])
                        prediction = client.post("/?page=prediction", data={
                            "air_temperature": 300, "process_temperature": 310,
                            "rotational_speed": 1500, "torque": 40, "tool_wear": 100,
                            "machine_type": "L",
                        })
                        self.assertIn(b"Model output:", prediction.data)
                        with client.session_transaction() as session:
                            token = session["maintenance_csrf"]
                        alert_id = conn.execute("SELECT MIN(id) FROM alerts").fetchone()[0]
                        response = client.post("/maintenance/action", data={
                            "csrf_token": token, "action": "acknowledge",
                            "alert_id": alert_id, "operator": "Test operator",
                        })
                        self.assertEqual(response.status_code, 303)
                        self.assertEqual(conn.execute(
                            "SELECT operator FROM alert_acknowledgements WHERE alert_id = ?", (alert_id,)
                        ).fetchone(), ("demo_operator",))
