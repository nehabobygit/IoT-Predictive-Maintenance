
import copy
import math
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from messaging import consumer


class ConsumerIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.run_id = str(uuid.uuid4())

        self.original_db_path = consumer.DB_PATH
        self.original_alert_times = consumer.last_alert_time.copy()

        consumer.DB_PATH = Path(self.temp_dir.name) / "test.db"
        consumer.last_alert_time.clear()

        consumer.create_database()

    def tearDown(self):
        consumer.DB_PATH = self.original_db_path

        consumer.last_alert_time.clear()
        consumer.last_alert_time.update(self.original_alert_times)

        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def message(self, **changes):
        readings = {
            "temperature": 40.0,
            "vibration": 3.0,
            "humidity": 50.0,
            "pressure": 4.0,
            "current": 10.0,
        }

        message = {
            "message_type": "sensor_reading",
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "asset_id": "SIM-MOTOR-001",
            "source": "simulated_sensor",
            "timestamp": "2026-11-21T10:00:00.000Z",
            "source_timestamp": None,
            "units": {
                "temperature": "°C",
                "vibration": "mm/s",
                "humidity": "%",
                "pressure": "bar",
                "current": "A",
            },
            "synthetic_fields": list(readings.keys()),
            "source_channels": {
                key: "simulated_" + key
                for key in readings
            },
            "readings": readings,
            "faults": [],
            "actual_anomaly": 0,
        }

        message.update(changes)
        return message

    def count(self, table):
        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            result = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()

            return result[0]
        finally:
            conn.close()

    def high_temperature_alert_count(self):
        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            result = conn.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE sensor = 'temperature'
                AND severity = 'HIGH'
                """
            ).fetchone()

            return result[0]
        finally:
            conn.close()

    def test_empty_database_creation(self):
        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                )
            }
        finally:
            conn.close()

        self.assertTrue(
            {"sensor_readings", "alerts", "predictions"} <= tables
        )

    def test_valid_sensor_message(self):
        consumer.process_sensor_message(self.message())

        self.assertEqual(
            self.count("sensor_readings"),
            1
        )

    def test_duplicate_event_is_ignored(self):
        message = self.message()

        consumer.process_sensor_message(message)
        consumer.process_sensor_message(
            copy.deepcopy(message)
        )

        self.assertEqual(
            self.count("sensor_readings"),
            1
        )

    def test_missing_sensor_rejected(self):
        message = self.message()
        del message["readings"]["temperature"]

        with self.assertRaises(ValueError):
            consumer.process_sensor_message(message)

        self.assertEqual(
            self.count("sensor_readings"),
            0
        )

    def test_nan_rejected(self):
        message = self.message()
        message["readings"]["temperature"] = math.nan

        with self.assertRaises(ValueError):
            consumer.process_sensor_message(message)

        self.assertEqual(
            self.count("sensor_readings"),
            0
        )

    def test_infinity_rejected(self):
        message = self.message()
        message["readings"]["temperature"] = math.inf

        with self.assertRaises(ValueError):
            consumer.process_sensor_message(message)

        self.assertEqual(
            self.count("sensor_readings"),
            0
        )

    def test_invalid_anomaly_label_rejected(self):
        message = self.message(actual_anomaly=2)

        with self.assertRaises(ValueError):
            consumer.process_sensor_message(message)

        self.assertEqual(
            self.count("sensor_readings"),
            0
        )

    def test_anomaly_creates_alert(self):
        baseline = [
            39.0,
            40.0,
            41.0,
            39.5,
            40.5,
            40.0,
        ]

        for temperature in baseline:
            message = self.message()
            message["readings"]["temperature"] = temperature

            consumer.process_sensor_message(message)

        before = self.count("alerts")

        spike = self.message(actual_anomaly=1)
        spike["readings"]["temperature"] = 75.0

        consumer.process_sensor_message(spike)

        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            alert = conn.execute(
                """
                SELECT sensor, severity
                FROM alerts
                WHERE event_id = ?
                """,
                (spike["event_id"],)
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(alert)
        self.assertEqual(alert[0], "temperature")
        self.assertEqual(alert[1], "HIGH")

        self.assertGreater(
            self.count("alerts"),
            before
        )

    def test_real_alert_cooldown(self):
        baseline = [
            39.0,
            40.0,
            41.0,
            39.5,
            40.5,
            40.0,
        ]

        for temperature in baseline:
            message = self.message()
            message["readings"]["temperature"] = temperature

            consumer.process_sensor_message(message)

        # Each spike uses the same baseline so that
        # the severity remains HIGH.
        #
        # 100 seconds: first HIGH alert is created.
        # 110 seconds: repeated HIGH alert is suppressed.
        # 131 seconds: cooldown expires, new HIGH alert allowed.

        test_cases = [
            (100.0, 1),
            (110.0, 1),
            (131.0, 2),
        ]

        for clock, expected_count in test_cases:
            message = self.message(actual_anomaly=1)
            message["readings"]["temperature"] = 75.0

            with patch.object(
                consumer.time,
                "monotonic",
                return_value=clock
            ):
                consumer.process_sensor_message(message)

            actual_count = self.high_temperature_alert_count()

            self.assertEqual(
                actual_count,
                expected_count,
                f"Incorrect HIGH alert count at {clock} seconds"
            )

            # Remove only the test spike reading.
            # This preserves the original baseline.
            # The alert record remains for cooldown verification.
            conn = sqlite3.connect(consumer.DB_PATH)

            try:
                conn.execute(
                    """
                    DELETE FROM sensor_readings
                    WHERE event_id = ?
                    """,
                    (message["event_id"],)
                )
                conn.commit()
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
