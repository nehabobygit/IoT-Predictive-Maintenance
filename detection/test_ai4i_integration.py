
import copy
import math
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from messaging import consumer
from messaging.message_contract import (
    AI4I_UNITS,
    build_metadata,
)


class AI4IIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        )

        self.original_db_path = consumer.DB_PATH
        consumer.DB_PATH = Path(self.temp_dir.name) / "ai4i_test.db"

        consumer.create_database()
        self.run_id = str(uuid.uuid4())

    def tearDown(self):
        consumer.DB_PATH = self.original_db_path

        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def message(self):
        metadata = build_metadata(
            message_type="ai4i_replay",
            source="ai4i_replay",
            run_id=self.run_id,
            asset_id=None,
            units=AI4I_UNITS,
            synthetic_fields=[],
            source_channels={
                key: key
                for key in AI4I_UNITS
            },
        )

        metadata.update({
            "readings": {
                "air_temperature": 298.1,
                "process_temperature": 308.6,
                "rotational_speed": 1551.0,
                "torque": 42.8,
                "tool_wear": 0.0,
            },
            "udi": 1,
            "product_id": "M14860",
            "machine_type": "M",
            "actual_failure": 0,
        })

        return metadata

    def count_predictions(self):
        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM predictions"
            ).fetchone()
            return result[0]
        finally:
            conn.close()

    def process_with_mock_model(self, message, score=0.2):
        with patch.object(
            consumer,
            "load_ai4i_model",
            return_value={
                "trees": [],
                "threshold": 0.76,
            }
        ), patch.object(
            consumer,
            "predict_forest",
            return_value=[score]
        ):
            consumer.process_ai4i_message(message)

    def test_valid_prediction_saved(self):
        self.process_with_mock_model(self.message())

        self.assertEqual(
            self.count_predictions(),
            1
        )

    def test_prediction_fields_saved_correctly(self):
        message = self.message()

        self.process_with_mock_model(message, score=0.9)

        conn = sqlite3.connect(consumer.DB_PATH)

        try:
            row = conn.execute(
                """
                SELECT failure_score, threshold,
                       predicted_failure, actual_failure,
                       correct, source
                FROM predictions
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertAlmostEqual(row[0], 0.9)
        self.assertAlmostEqual(row[1], 0.76)
        self.assertEqual(row[2], 1)
        self.assertEqual(row[3], 0)
        self.assertEqual(row[4], 0)
        self.assertEqual(row[5], "ai4i_replay")

    def test_duplicate_event_ignored(self):
        message = self.message()

        self.process_with_mock_model(message)
        self.process_with_mock_model(
            copy.deepcopy(message)
        )

        self.assertEqual(
            self.count_predictions(),
            1
        )

    def test_missing_sensor_rejected(self):
        message = self.message()
        del message["readings"]["torque"]

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_nan_rejected(self):
        message = self.message()
        message["readings"]["torque"] = math.nan

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_infinity_rejected(self):
        message = self.message()
        message["readings"]["torque"] = math.inf

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_invalid_machine_type_rejected(self):
        message = self.message()
        message["machine_type"] = "X"

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_invalid_failure_label_rejected(self):
        message = self.message()
        message["actual_failure"] = 2

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_invalid_udi_rejected(self):
        message = self.message()
        message["udi"] = -1

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_missing_product_id_rejected(self):
        message = self.message()
        message["product_id"] = ""

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_wrong_source_rejected(self):
        message = self.message()
        message["source"] = "simulated_sensor"

        with self.assertRaises(ValueError):
            self.process_with_mock_model(message)

        self.assertEqual(self.count_predictions(), 0)

    def test_feature_engineering(self):
        message = self.message()

        with patch.object(
            consumer,
            "load_ai4i_model",
            return_value={
                "trees": [],
                "threshold": 0.76,
            }
        ), patch.object(
            consumer,
            "predict_forest",
            return_value=[0.2]
        ) as predictor:

            consumer.process_ai4i_message(message)

            features = predictor.call_args.args[1][0]

        self.assertEqual(len(features), 10)
        self.assertEqual(features[5:8], [0, 1, 0])

        self.assertAlmostEqual(
            features[8],
            308.6 - 298.1
        )

        self.assertAlmostEqual(
            features[9],
            42.8 * 1551 / 1000
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
