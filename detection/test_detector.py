import unittest
from detection.detection_engine import (
    calculate_z_score,
    classify_severity,
    ALERT_COOLDOWN
)


class DetectorTests(unittest.TestCase):

    def test_normal_reading(self):
        score = calculate_z_score(
            [10, 11, 9, 10, 11], 10
        )
        self.assertLess(abs(score), 1.5)

    def test_spike(self):
        score = calculate_z_score(
            [10, 11, 9, 10, 11], 25
        )
        self.assertGreater(abs(score), 5)

    def test_insufficient_history(self):
        self.assertIsNone(
            calculate_z_score([10, 11], 25)
        )

    def test_invalid_reading(self):
        self.assertIsNone(
            calculate_z_score([10] * 10, float("nan"))
        )

    def test_severity(self):
        self.assertEqual(classify_severity(1.6), "LOW")
        self.assertEqual(classify_severity(3.5), "MEDIUM")
        self.assertEqual(classify_severity(5), "HIGH")
        self.assertEqual(classify_severity(-5), "HIGH")

    def test_cooldown_rule(self):
        previous = 100

        self.assertLess(110 - previous, ALERT_COOLDOWN)
        self.assertLess(129 - previous, ALERT_COOLDOWN)
        self.assertGreaterEqual(
            130 - previous, ALERT_COOLDOWN
        )

    def test_severity_escalation_rule(self):
        self.assertNotEqual(
            classify_severity(2),
            classify_severity(6)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)