"""Correlated five-sensor telemetry and repeatable fault scenarios."""
import math
import random

PROFILES = {
    "SIM-MOTOR-001": (39.0, 2.6, 47.0, 4.4, 11.0),
    "SIM-MOTOR-002": (42.0, 3.4, 54.0, 5.0, 14.0),
    "SIM-MOTOR-003": (36.0, 2.0, 59.0, 3.6, 8.5),
}
SENSORS = ("temperature", "vibration", "humidity", "pressure", "current")
EPISODE_LENGTH = 100
HORIZON = 6
INTERVAL_SECONDS = 2


class MachineSimulator:
    def __init__(self, asset_id, *, seed=None, offset=0):
        self.profile = PROFILES[asset_id]
        self.random = random.Random(seed)
        self.index = offset
        self.episode = None

    def sample(self):
        rng = self.random
        episode, phase = divmod(self.index, EPISODE_LENGTH)
        self.index += 1
        if episode != self.episode:
            self.episode = episode
            self.onset = rng.randint(52, 60)
            self.failure_at = self.onset + rng.randint(15, 25)
            self.load_phase = rng.uniform(0, 2 * math.pi)
            self.degrades = rng.random() < 0.8
            self.drift_direction = rng.choice((-1, 1))
            self.sensor_offsets = [rng.uniform(-scale, scale) for scale in (1.5, .35, 3, .25, 1.2)]

        load = math.sin(phase / 6 + self.load_phase) + .4 * math.sin(phase / 13)
        base = {
            sensor: round(value + offset + scale * load + rng.gauss(0, noise), 2)
            for sensor, value, offset, scale, noise in zip(
                SENSORS, self.profile, self.sensor_offsets,
                (1.0, .35, .45, .2, 1.65), (.45, .2, .55, .08, .35)
            )
        }
        readings = base.copy()
        faults = []

        def change(sensor, amount, fault):
            readings[sensor] = round(readings[sensor] + amount, 2)
            faults.append((sensor, fault, base[sensor], readings[sensor]))

        if phase == 15:
            change("temperature", 24, "sudden_spike")
        if 21 <= phase <= 27:
            change("temperature", 2.5 * (phase - 20), "gradual_rise")
        if phase in (31, 33):
            change("vibration", rng.uniform(9, 15), "irregular_vibration")
        if 36 <= phase <= 46:
            change("humidity", self.drift_direction * 2.3 * (phase - 35), "sensor_drift")
        if phase == 48:
            change("pressure", 1.0 - base["pressure"], "pressure_drop")
        if phase == 50:
            change("current", 28 - base["current"], "current_surge")
        if phase == 89:
            change("vibration", 12, "irregular_vibration")
            change("current", 30 - base["current"], "current_surge")

        failed = self.degrades and self.failure_at <= phase <= self.failure_at + 3
        if self.degrades and self.onset < phase <= self.failure_at + 3:
            wear = min(1.2, (phase - self.onset) / (self.failure_at - self.onset))
            for sensor, amplitude in {
                "temperature": 17, "vibration": 8, "pressure": -2.1, "current": 11,
            }.items():
                change(sensor, amplitude * wear ** 1.4, "progressive_degradation")

        return readings, faults, failed
