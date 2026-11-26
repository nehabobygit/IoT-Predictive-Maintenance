"""Controlled registry for telemetry streams with stable asset identifiers."""
import json
import os
from pathlib import Path

from sensors.machine_simulator import PROFILES

DEFAULT_ASSETS = {
    asset: {"source": "simulated_sensor", "name": f"Simulated motor {asset[-3:]}", "kind": "motor"}
    for asset in PROFILES
}
DEFAULT_ASSETS["SKAB-VALVE1"] = {"source": "skab_replay", "name": "SKAB valve 1", "kind": "recorded test rig"}


def load_assets():
    assets = DEFAULT_ASSETS.copy()
    config = os.getenv("IOT_ASSET_REGISTRY")
    if config:
        extra = json.loads(Path(config).read_text(encoding="utf-8-sig"))
        if not isinstance(extra, dict):
            raise ValueError("The asset registry must be a JSON object.")
        for asset, metadata in extra.items():
            if (not 0 < len(asset) <= 100 or asset in assets or not isinstance(metadata, dict)
                or metadata.get("source") not in ("simulated_sensor", "skab_replay")
                or not all(isinstance(metadata.get(key), str) and metadata[key].strip()
                           for key in ("name", "kind"))):
                raise ValueError(f"Invalid or duplicate asset registration: {asset}")
        assets.update(extra)
    return assets


ASSETS = load_assets()
