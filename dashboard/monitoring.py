"""Read the latest machine telemetry and model evaluation for the dashboard."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from messaging.asset_registry import ASSETS

ROOT = Path(__file__).resolve().parents[1]
FRESHNESS = timedelta(minutes=2)


def model_evaluations():
    reports = {}
    for key, filename in (("ai4i", "ai4i_improved_metrics.json"),
                          ("live", "live_maintenance_metrics.json"),
                          ("simulator", "simulator_grouped_metrics.json"),
                          ("skab", "skab_grouped_metrics.json")):
        with (ROOT / "results" / filename).open(encoding="utf-8") as stream:
            reports[key] = json.load(stream)
    return reports


def monitoring_snapshot(conn, asset=None):
    parameters = (asset,) if asset else ()
    asset_filter = " AND asset_id = ?" if asset else ""
    now = datetime.now(timezone.utc)
    cutoff = (now - FRESHNESS).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    latest = conn.execute("""
        SELECT r.id, r.asset_id, r.timestamp, r.source, r.units_json,
               r.temperature, r.vibration, r.humidity, r.pressure, r.current,
               f.score, f.threshold, f.horizon_seconds
        FROM sensor_readings r
        LEFT JOIN maintenance_forecasts f ON f.reading_id = r.id
        WHERE r.id IN (
            SELECT MAX(id) FROM sensor_readings
            WHERE asset_id IS NOT NULL AND asset_id != '' """ + asset_filter + """
            GROUP BY asset_id
        )
        ORDER BY r.asset_id
    """, parameters).fetchall()
    counts = {"healthy": 0, "attention": 0, "critical": 0, "offline": 0, "unrated": 0}
    machines = []
    active_anomalies = 0
    sensors = ("temperature", "vibration", "humidity", "pressure", "current")
    for row in latest:
        reading_id, asset_id, timestamp, source, units_json = row[:5]
        try:
            age = now - datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            fresh = timedelta(0) <= age <= FRESHNESS
        except (ValueError, TypeError, AttributeError):
            fresh = False
        events = [
            dict(zip(("sensor", "category", "severity", "explanation"), event))
            for event in conn.execute("""
                SELECT sensor, category, severity, explanation
                FROM anomaly_events WHERE reading_id = ? ORDER BY sensor
            """, (reading_id,))
        ] if fresh else []
        active_anomalies += len(events)
        score, threshold, seconds = row[10:13]
        if not fresh:
            status = "offline"
        elif any(event["severity"] == "HIGH" for event in events):
            status = "critical"
        elif events or (score is not None and score >= threshold):
            status = "attention"
        elif source == "simulated_sensor":
            status = "healthy"
        else:
            status = "unrated"
        counts[status] += 1
        try:
            units = json.loads(units_json or "{}")
        except (ValueError, TypeError):
            units = {}
        machines.append({
            "asset_id": asset_id, "metadata": ASSETS.get(asset_id), "timestamp": timestamp, "source": source,
            "status": status, "readings": dict(zip(sensors, row[5:10])), "units": units,
            "anomalies": events, "forecast": {
                "score": score, "threshold": threshold, "horizon_seconds": seconds,
                "warning": score >= threshold,
            } if fresh and score is not None else None,
        })
    active_alerts = conn.execute("""
        SELECT COUNT(*) FROM alerts
        WHERE timestamp >= ? AND timestamp <= ?
          AND id NOT IN (SELECT alert_id FROM alert_acknowledgements)
    """ + asset_filter, (cutoff, now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), *parameters)).fetchone()[0]
    return {"machines": machines, "counts": counts, "active_anomalies": active_anomalies,
            "active_alerts": active_alerts}
