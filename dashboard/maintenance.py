"""Transactional maintenance mutations and attribution."""
import json
from datetime import datetime


def migrate(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(maintenance_tasks)")}
    if "alert_id" not in columns:
        conn.execute("ALTER TABLE maintenance_tasks ADD COLUMN alert_id INTEGER REFERENCES alerts(id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_audit (
            id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, actor TEXT NOT NULL,
            action TEXT NOT NULL, alert_id INTEGER REFERENCES alerts(id),
            task_id INTEGER REFERENCES maintenance_tasks(id), details TEXT NOT NULL
        )
    """)


def apply_action(conn, form, actor, now):
    action = form.get("action")

    def audit(kind, alert_id, task_id, details):
        conn.execute("""
            INSERT INTO maintenance_audit (timestamp, actor, action, alert_id, task_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, actor, kind, alert_id, task_id, json.dumps(details, sort_keys=True)))

    if action in ("acknowledge", "schedule"):
        alert_id = int(form.get("alert_id", ""))
        alert = conn.execute("SELECT asset_id, recommendation FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if alert is None:
            raise ValueError("Alert not found.")
        asset, recommendation = alert
        if action == "acknowledge":
            result = conn.execute("INSERT OR IGNORE INTO alert_acknowledgements VALUES (?, ?, ?)",
                                  (alert_id, actor, now))
            if result.rowcount:
                audit("acknowledge", alert_id, None, {"asset": asset})
                return "Alert acknowledged."
            return "Alert was already acknowledged."
        engineer, priority = assignment(form)
        scheduled = form.get("scheduled_for", "")
        datetime.fromisoformat(scheduled)
        description = form.get("description", "").strip() or recommendation
        if not description or len(description) > 1000:
            raise ValueError("Enter a task description.")
        task = conn.execute("""
            INSERT INTO maintenance_tasks
            (created_at, asset_id, priority, assigned_to, scheduled_for, description, status, alert_id)
            VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED', ?)
        """, (now, asset, priority, engineer, scheduled, description, alert_id)).lastrowid
        audit("schedule", alert_id, task, {"asset": asset, "engineer": engineer, "priority": priority})
        return "Maintenance task scheduled."

    if action not in ("complete", "update"):
        raise ValueError("Unknown maintenance action.")
    task = int(form.get("task_id", ""))
    previous = conn.execute("""
        SELECT alert_id, assigned_to, priority FROM maintenance_tasks WHERE id=? AND status='SCHEDULED'
    """, (task,)).fetchone()
    if not previous:
        raise ValueError("Task not found or already completed.")
    alert_id, old_engineer, old_priority = previous
    if action == "complete":
        notes = form.get("completion_notes", "").strip()
        if not 1 <= len(notes) <= 1000:
            raise ValueError("Enter the work performed.")
        conn.execute("""
            UPDATE maintenance_tasks SET status='COMPLETED', completed_at=?, completion_notes=? WHERE id=?
        """, (now, notes, task))
        audit("complete", alert_id, task, {"notes": notes})
        return "Maintenance task marked complete."

    engineer, priority = assignment(form)
    conn.execute("UPDATE maintenance_tasks SET assigned_to=?, priority=? WHERE id=?",
                 (engineer, priority, task))
    audit("update", alert_id, task, {"previous_engineer": old_engineer, "engineer": engineer,
                                   "previous_priority": old_priority, "priority": priority})
    return "Maintenance assignment updated."


def assignment(form):
    engineer = form.get("assigned_to", "").strip()
    priority = form.get("priority")
    if not 1 <= len(engineer) <= 80 or priority not in ("LOW", "MEDIUM", "HIGH"):
        raise ValueError("Enter an engineer and priority.")
    return engineer, priority
