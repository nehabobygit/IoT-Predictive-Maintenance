"""Shared, versioned MQTT message metadata for the predictive-maintenance project."""

from datetime import datetime, timezone
import uuid

from messaging.asset_registry import ASSETS

SCHEMA_VERSION = "1.0"

SENSOR_UNITS = {
    "simulated_sensor": {
        "temperature": "°C",
        "vibration": "mm/s",
        "humidity": "%",
        "pressure": "bar",
        "current": "A",
    },
    "skab_replay": {
        "temperature": "°C",
        "vibration": "g",
        "humidity": "%",
        "pressure": "bar",
        "current": "A",
    },
}

AI4I_UNITS = {
    "air_temperature": "K",
    "process_temperature": "K",
    "rotational_speed": "rpm",
    "torque": "Nm",
    "tool_wear": "min",
}

EXPECTED_MESSAGE_TYPES = {
    "simulated_sensor": "sensor_reading",
    "skab_replay": "sensor_reading",
    "ai4i_replay": "ai4i_replay",
}


def new_id():
    """Return a UUID4 string for an event or replay run."""
    return str(uuid.uuid4())


def utc_now_iso():
    """Return an ISO-8601 UTC timestamp with an explicit Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_metadata(
    *,
    message_type,
    source,
    run_id,
    asset_id,
    units,
    synthetic_fields,
    source_channels,
    source_timestamp=None,
):
    """Build the common metadata envelope used by all project publishers."""
    if source not in EXPECTED_MESSAGE_TYPES:
        raise ValueError(f"Unsupported message source: {source}")

    if message_type != EXPECTED_MESSAGE_TYPES[source]:
        raise ValueError(f"Unexpected message type for source {source}: {message_type}")

    return {
        "message_type": message_type,
        "schema_version": SCHEMA_VERSION,
        "event_id": new_id(),
        "run_id": str(run_id),
        "asset_id": asset_id,
        "source": source,
        "timestamp": utc_now_iso(),
        "source_timestamp": source_timestamp,
        "units": dict(units),
        "synthetic_fields": list(synthetic_fields),
        "source_channels": dict(source_channels),
    }


def _validate_uuid(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Metadata field '{field_name}' must be a non-empty UUID string.")
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"Metadata field '{field_name}' is not a valid UUID.") from error


def validate_metadata(data, *, expected_source=None):
    """Validate common message metadata and return the validated source name."""
    if not isinstance(data, dict):
        raise ValueError("MQTT payload must be a JSON object.")

    required = (
        "message_type", "schema_version", "event_id", "run_id", "asset_id",
        "source", "timestamp", "source_timestamp", "units",
        "synthetic_fields", "source_channels",
    )
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("Message is missing metadata fields: " + ", ".join(missing))

    source = data["source"]
    if source not in EXPECTED_MESSAGE_TYPES:
        raise ValueError(f"Unsupported message source: {source}")
    if expected_source is not None and source != expected_source:
        raise ValueError(f"Expected source '{expected_source}', received '{source}'.")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {data['schema_version']}")
    if data["message_type"] != EXPECTED_MESSAGE_TYPES[source]:
        raise ValueError(f"Invalid message_type for source '{source}'.")

    _validate_uuid(data["event_id"], "event_id")
    _validate_uuid(data["run_id"], "run_id")

    timestamp = data["timestamp"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("Message timestamp is missing.")
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Message timestamp must be valid ISO-8601.") from error
    if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
        raise ValueError("Message timestamp must include a timezone; UTC is required.")
    if parsed_timestamp.utcoffset().total_seconds() != 0:
        raise ValueError("Message timestamp must be UTC.")

    source_timestamp = data["source_timestamp"]
    if source_timestamp is not None and not isinstance(source_timestamp, str):
        raise ValueError("source_timestamp must be a string or null.")
    if source == "skab_replay" and not source_timestamp:
        raise ValueError("SKAB replay messages must preserve their original source timestamp.")

    units = data["units"]
    if not isinstance(units, dict) or not units:
        raise ValueError("Message units must be a non-empty object.")
    expected_units = SENSOR_UNITS.get(source) if source in SENSOR_UNITS else AI4I_UNITS
    if units != expected_units:
        raise ValueError(f"Units do not match the declared source '{source}'.")

    synthetic_fields = data["synthetic_fields"]
    source_channels = data["source_channels"]
    if not isinstance(synthetic_fields, list) or not all(isinstance(item, str) for item in synthetic_fields):
        raise ValueError("synthetic_fields must be a list of strings.")
    if not isinstance(source_channels, dict) or not source_channels:
        raise ValueError("source_channels must be a non-empty object.")

    asset_id = data["asset_id"]
    if source in SENSOR_UNITS:
        if not isinstance(asset_id, str) or ASSETS.get(asset_id, {}).get("source") != source:
            raise ValueError("Asset is not registered for the declared source.")
    elif source == "ai4i_replay" and asset_id is not None:
        raise ValueError("AI4I replay records do not contain a physical asset ID; asset_id must be null.")

    return source
