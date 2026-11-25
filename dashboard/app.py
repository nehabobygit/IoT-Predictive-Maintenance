import sqlite3
import json
import pickle
import secrets
import os
import hmac
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, session, abort
from messaging.model_security import verify_ai4i_model

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Local-session CSRF protection; restart invalidates sessions.

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sensor_readings.db"
MODEL_PATH = BASE_DIR / "models" / "ai4i_random_forest.pkl"

SENSORS = [
    "temperature",
    "vibration",
    "humidity",
    "pressure",
    "current"
]

SENSOR_LABELS = {
    "temperature": "Temperature",
    "vibration": "Vibration",
    "humidity": "Humidity",
    "pressure": "Pressure",
    "current": "Current"
}

UNITS = {
    "temperature": "°C",
    "vibration": "mm/s",
    "humidity": "%",
    "pressure": "bar",
    "current": "A"
}

PAGES = [
    ("overview", "Overview", "layout-dashboard"),
    ("sensors", "Live Sensors", "activity"),
    ("alerts", "Maintenance Alerts", "alert-triangle"),
    ("history", "Reading History", "database"),
    ("prediction", "Machine Failure Prediction", "brain-circuit"),
    ("ai4i_replay", "Replay Prediction Results", "chart-no-axes-combined"),
    ("maintenance", "Maintenance Management", "clipboard-check"),
    ("notifications", "Notifications", "bell")
]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Industrial Predictive Maintenance</title>

    <meta name="viewport" content="width=device-width, initial-scale=1">
    {% if page not in ("prediction", "maintenance") %}<meta http-equiv="refresh" content="5">{% endif %}

    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f6f8;
            color: #263238;
        }

        /* SIDEBAR */

        .sidebar {
            width: 245px;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            background: #174e53;
            color: white;
            padding: 25px 15px;
            display: flex;
            flex-direction: column;
            z-index: 10;
        }

        .brand {
            font-size: 19px;
            font-weight: bold;
            line-height: 1.5;
            padding: 0 12px 25px;
            border-bottom: 1px solid #477276;
        }

        .brand small {
            display: block;
            font-size: 11px;
            font-weight: normal;
            color: #c5d9da;
            margin-top: 5px;
        }

        .nav-title {
            font-size: 10px;
            color: #b8d0d1;
            letter-spacing: 1.5px;
            padding: 25px 12px 10px;
        }

        .nav-link {
            display: block;
            padding: 13px 12px;
            margin: 3px 0;
            border-radius: 7px;
            text-decoration: none;
            color: #e3eeee;
            font-size: 14px;
            transition: 0.2s;
        }

        .nav-link:hover {
            background: #28666b;
            color: white;
        }

        .nav-link.active {
            background: #e4f0f0;
            color: #174e53;
            font-weight: bold;
        }


        /* MAIN CONTENT */

        .main {
            margin-left: 245px;
            padding: 28px 32px;
            min-height: 100vh;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
        }

        h1 {
            color: #1f5e63;
            font-size: 26px;
            margin: 0 0 7px;
        }

        h2 {
            color: #1f5e63;
            font-size: 19px;
            margin: 28px 0 8px;
        }

        .subtitle {
            color: #718087;
            font-size: 13px;
            line-height: 1.5;
        }


        .info-banner {
            background: #e5f0f1;
            border-left: 4px solid #1f5e63;
            padding: 14px 17px;
            border-radius: 6px;
            margin-bottom: 24px;
            font-size: 13px;
            line-height: 1.6;
        }

        .section-description {
            color: #718087;
            font-size: 13px;
            margin: 0 0 17px;
            line-height: 1.5;
        }

        /* CARDS */

        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 14px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
        }

        .card {
            background: white;
            padding: 18px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
            min-width: 0;
        }

        .sensor-card {
            border-top: 4px solid #1f5e63;
        }

        .card-label {
            font-size: 13px;
            font-weight: bold;
            color: #52636a;
        }

        .sensor-value {
            font-size: 24px;
            font-weight: bold;
            color: #1f5e63;
            margin: 13px 0;
        }

        .small-text {
            font-size: 12px;
            color: #718087;
            line-height: 1.6;
        }

        .summary-card {
            border-left: 4px solid #1f5e63;
        }

        .summary-number {
            font-size: 27px;
            font-weight: bold;
            margin-top: 12px;
        }

        .high-text {
            color: #dc2626;
        }

        .medium-text {
            color: #e67e22;
        }

        .low-text {
            color: #b8860b;
        }

        /* GRAPHS */

        .graph-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
        }

        .graph-card {
            background: white;
            padding: 12px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
            min-width: 0;
        }

        .chart {
            height: 320px;
            width: 100%;
        }

        /* TABLES */

        .table-container {
            width: 100%;
            overflow-x: auto;
            background: white;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
            margin-top: 15px;
        }

        table {
            width: 100%;
            min-width: 750px;
            border-collapse: collapse;
        }

        th {
            background: #1f5e63;
            color: white;
            text-align: left;
            padding: 13px;
            font-size: 12px;
            white-space: nowrap;
        }

        td {
            padding: 12px 13px;
            border-bottom: 1px solid #e6eaed;
            font-size: 12px;
            vertical-align: top;
        }

        tr:hover {
            background: #f1f7f7;
        }

        .recommendation {
            min-width: 260px;
            white-space: normal;
            line-height: 1.5;
        }

        .HIGH {
            color: #dc2626;
            font-weight: bold;
        }

        .MEDIUM {
            color: #e67e22;
            font-weight: bold;
        }

        .LOW {
            color: #b8860b;
            font-weight: bold;
        }

        .normal-text {
            color: #26834a;
            font-weight: bold;
        }

        .failure-text {
            color: #dc2626;
            font-weight: bold;
        }

        .correct-text {
            color: #26834a;
            font-weight: bold;
        }

        .incorrect-text {
            color: #dc2626;
            font-weight: bold;
        }

        /* FILTERS */

        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            align-items: end;
            gap: 12px;
            background: white;
            padding: 16px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .filter-group label {
            font-size: 12px;
            font-weight: bold;
            color: #52636a;
        }

        select {
            padding: 10px;
            min-width: 155px;
            border: 1px solid #ccd5d9;
            border-radius: 6px;
            background: white;
            color: #263238;
        }

        .filter-button {
            padding: 10px 17px;
            border: none;
            border-radius: 6px;
            background: #1f5e63;
            color: white;
            cursor: pointer;
        }

        .filter-button:hover {
            background: #174e53;
        }

        .reset-link {
            color: #1f5e63;
            font-size: 13px;
            padding: 10px;
            text-decoration: none;
        }

        .pagination {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-top: 16px;
            padding: 12px 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 6px #dfe4e7;
        }

        .pagination-info {
            color: #718087;
            font-size: 12px;
        }

        .pagination-links {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .pagination-links a,
        .pagination-links span {
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 12px;
            text-decoration: none;
        }

        .pagination-links a {
            background: #1f5e63;
            color: white;
        }

        .pagination-links a:hover {
            background: #174e53;
        }

        .pagination-links span {
            color: #52636a;
            background: #f3f6f8;
        }

        /* MACHINE FAILURE PREDICTION */

        .prediction-form {
            background: white;
            padding: 22px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
            max-width: 850px;
        }

        .prediction-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
        }

        .prediction-field {
            display: flex;
            flex-direction: column;
            gap: 7px;
        }

        .prediction-field label {
            font-size: 12px;
            font-weight: bold;
            color: #52636a;
        }

        .prediction-field input,
        .prediction-field select {
            width: 100%;
            min-width: 0;
            padding: 11px;
            border: 1px solid #ccd5d9;
            border-radius: 6px;
            background: white;
            color: #263238;
        }

        .prediction-submit {
            margin-top: 20px;
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            background: #1f5e63;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }

        .prediction-submit:hover {
            background: #174e53;
        }

        .prediction-result {
            margin-top: 22px;
            padding: 20px;
            border-radius: 9px;
            background: #e5f0f1;
            border-left: 4px solid #1f5e63;
            max-width: 850px;
        }

        .prediction-result.failure {
            background: #fff0f0;
            border-left-color: #dc2626;
        }

        .prediction-result.normal {
            background: #edf7f0;
            border-left-color: #26834a;
        }

        .prediction-error {
            margin-top: 18px;
            padding: 14px;
            border-radius: 7px;
            background: #fff0f0;
            color: #b42318;
            font-size: 13px;
        }

        /* OTHER */

        .severity-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
        }

        .severity-card {
            background: white;
            padding: 18px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
            line-height: 1.6;
            font-size: 13px;
        }

        .empty-message {
            background: white;
            padding: 22px;
            border-radius: 8px;
            color: #718087;
            font-size: 13px;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        .detail-card {
            background: white;
            padding: 18px;
            border-radius: 9px;
            box-shadow: 0 2px 6px #dfe4e7;
        }

        .detail-value {
            color: #1f5e63;
            font-weight: bold;
            margin-top: 9px;
            overflow-wrap: anywhere;
        }

        .footer {
            margin-top: 35px;
            padding: 20px;
            text-align: center;
            color: #819096;
            font-size: 11px;
        }


        /* NOTIFICATIONS - additive styling only */
        .notification-bell { position:relative; display:inline-flex; align-items:center; justify-content:center;
            width:45px; height:45px; border:1px solid #dce6e8; border-radius:12px;
            background:white; color:#1f5e63; text-decoration:none; box-shadow:0 2px 6px #dfe4e7; }
        .notification-bell:hover { background:#e5f0f1; }
        .notification-count { position:absolute; right:-7px; top:-7px; min-width:22px; height:22px;
            padding:3px 5px; border-radius:14px; background:#dc2626; color:white; font-size:11px;
            font-weight:bold; text-align:center; }
        .notification-stream { max-width:900px; background:white; border:1px solid #e0e8e9;
            border-radius:12px; padding:20px; box-shadow:0 2px 6px #dfe4e7; }
        .notification-item { display:flex; align-items:flex-start; gap:12px; margin-bottom:22px; }
        .notification-avatar { flex:0 0 38px; height:38px; display:grid; place-items:center;
            border-radius:50%; background:#e5f0f1; color:#1f5e63; font-weight:bold; }
        .notification-body { min-width:0; flex:1; }
        .notification-meta { color:#718087; font-size:12px; margin:0 0 7px; overflow-wrap:anywhere; }
        .notification-bubble { background:#f5f8f9; border-left:4px solid #b8860b;
            border-radius:4px 10px 10px 10px; padding:15px; line-height:1.65; font-size:13px; }
        .notification-bubble.high { border-left-color:#dc2626; }
        .notification-bubble.medium { border-left-color:#e67e22; }
        .notification-bubble.low { border-left-color:#b8860b; }
        .notification-bubble p { margin:6px 0; overflow-wrap:anywhere; }
        .notification-heading { font-weight:bold; margin-bottom:8px; }

        /* MAINTENANCE MANAGEMENT */
        .maintenance-form { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
        .maintenance-form input, .maintenance-form select, .maintenance-form textarea {
            border: 1px solid #ccd5d9; border-radius: 6px; padding: 9px;
            font: inherit; max-width: 100%;
        }
        .maintenance-form textarea { min-width: 230px; min-height: 42px; }
        .maintenance-note { color: #718087; font-size: 12px; margin-top: 8px; }
        .maintenance-success { padding: 12px; background: #edf7f0; border-radius: 7px; margin-bottom: 15px; }
        .maintenance-error { padding: 12px; background: #fff0f0; border-radius: 7px; margin-bottom: 15px; }

        @media (max-width: 1150px) {
            .sensor-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 800px) {
            .sidebar {
                width: 100%;
                height: auto;
                position: relative;
                padding: 15px;
            }

            .brand {
                padding-bottom: 12px;
            }

            .nav-title,
            .sidebar-footer {
                display: none;
            }

            .sidebar nav {
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                margin-top: 12px;
            }

            .nav-link {
                padding: 10px;
                font-size: 12px;
            }

            .main {
                margin-left: 0;
                padding: 20px 14px;
            }

            .topbar {
                align-items: flex-start;
                flex-direction: column;
            }

            .graph-grid,
            .severity-grid,
            .detail-grid,
            .prediction-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 520px) {
            .sensor-grid,
            .summary-grid {
                grid-template-columns: 1fr;
            }

            h1 {
                font-size: 22px;
            }
        }
    </style>
</head>

<body>

    <!-- SIDEBAR -->

    <aside class="sidebar">

        <div class="brand">
            INDUSTRIAL
            <br>
            MONITORING

            <small>Predictive Maintenance System</small>
        </div>

        <div class="nav-title">MAIN MENU</div>

        <nav>
            {% for key, label, icon in pages %}
                <a
                    class="nav-link {% if page == key %}active{% endif %}"
                    href="{{ url_for('dashboard', page=key, asset=selected_asset) }}"
                >
                    {{ label }}
                </a>
            {% endfor %}
        </nav>



    </aside>


    <!-- MAIN CONTENT -->

    <main class="main">

        <div class="topbar">

            <div>
                <h1>{{ page_title }}</h1>
                <div class="subtitle">{{ page_description }}</div>
            </div>
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
              <form method="GET" action="/" style="display:flex;align-items:center;gap:8px">
                <input type="hidden" name="page" value="{{ page }}">
                <label for="asset_selector" style="font-size:12px;font-weight:bold;color:#52636a">Machine</label>
                <select id="asset_selector" name="asset" aria-label="Select machine" onchange="this.form.submit()" style="min-width:170px">
                  <option value="all" {% if selected_asset == 'all' %}selected{% endif %}>All Machines</option>
                  {% for asset_id in available_assets %}
                  <option value="{{ asset_id }}" {% if selected_asset == asset_id %}selected{% endif %}>{{ asset_id }}</option>
                  {% endfor %}
                </select>
              </form>
            <a class="notification-bell" href="{{ url_for('dashboard', page='notifications', asset=selected_asset) }}"
               aria-label="View maintenance notifications" title="Maintenance notifications">
                <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/>
                    <path d="M10 21h4"/>
                </svg>
                {% if notification_unread > 0 %}<span class="notification-count">{{ '99+' if notification_unread > 99 else notification_unread }}</span>{% endif %}
            </a>
            </div>
        </div>


        {% if page == "overview" %}

            <div class="info-banner">
                <strong>System overview:</strong>
                Monitor equipment readings, review important
                maintenance alerts and identify unusual sensor behaviour.
                Alerts are early warning indicators, not confirmation
                that equipment has failed.
            </div>

            <h2>Equipment Status</h2>

            <div class="card" style="margin: 14px 0 18px; border-left: 4px solid {{ '#26834a' if machine_status == 'NORMAL' else '#e67e22' if machine_status == 'WARNING' else '#718087' }};">
                <div class="card-label">Current Machine Status</div>
                <div class="sensor-value" style="margin: 8px 0; color: {{ '#26834a' if machine_status == 'NORMAL' else '#e67e22' if machine_status == 'WARNING' else '#718087' }};">
                    {{ machine_status }}
                </div>
                <div class="small-text">{{ machine_status_detail }}</div>
            </div>

            <p class="section-description">
                Latest readings received from all five sensors. Asset: {{ latest_asset or "Unknown" }} | Source: {{ latest_source or "Unknown" }}.
            </p>

            {% if latest %}

                <div class="sensor-grid">

                    {% for sensor in sensors %}

                        <div class="card sensor-card">

                            <div class="card-label">
                                {{ sensor_labels[sensor] }}{% if sensor in latest_synthetic %} (synthetic){% endif %}
                            </div>

                            <div class="sensor-value">
                                {{ latest[sensor] }} {{ units[sensor] }}
                            </div>

                            <div class="small-text">
                                {% if last_alerts.get(sensor) %}
                                    Last alert:
                                    <strong class="{{ last_alerts[sensor][0] }}">
                                        {{ last_alerts[sensor][0] }}
                                    </strong>
                                    <br>
                                    {{ last_alerts[sensor][1] }}
                                {% else %}
                                    No alert recorded.
                                {% endif %}
                            </div>

                        </div>

                    {% endfor %}

                </div>

            {% else %}

                <div class="empty-message">
                    No sensor readings received yet.
                    Check the MQTT publisher and consumer.
                </div>

            {% endif %}


            <h2>Maintenance Alert Summary</h2>

            <p class="section-description">
                Historical alert counts stored in the database.
                These are not currently active alarms.
            </p>

            <div class="summary-grid">

                <div class="card summary-card">
                    <div class="card-label">Total Alerts</div>
                    <div class="summary-number">
                        {{ alert_counts["TOTAL"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">High Severity</div>
                    <div class="summary-number high-text">
                        {{ alert_counts["HIGH"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">Medium Severity</div>
                    <div class="summary-number medium-text">
                        {{ alert_counts["MEDIUM"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">Low Severity</div>
                    <div class="summary-number low-text">
                        {{ alert_counts["LOW"] }}
                    </div>
                </div>

            </div>


            <h2>Latest Maintenance Alerts</h2>

            <p class="section-description">
                The six most recent alerts requiring attention.
                Open Maintenance Alerts to view and filter all recent alerts.
            </p>

            {% if alerts %}

                <div class="table-container">
                    <table>
                        <tr>
                            <th>Time</th>
                            <th>Sensor</th>
                            <th>Asset / Source</th>
                            <th>Reading</th>
                            <th>Severity</th>
                            <th>Recommended Action</th>
                        </tr>

                        {% for alert in alerts[:6] %}
                            <tr>
                                <td>{{ alert[0] }}</td>
                                <td>{{ sensor_labels.get(alert[1], alert[1]) }}</td>
                                <td>{{ alert[7] or "Unknown" }} / {{ alert[8] or "Unknown" }}</td>
                                <td>{{ alert[2] }} {{ alert[6] or units.get(alert[1], "unit unknown") }}</td>
                                <td class="{{ alert[4] }}">
                                    {{ alert[4] }}
                                </td>
                                <td class="recommendation">
                                    {{ alert[5] }}
                                </td>
                            </tr>
                        {% endfor %}
                    </table>
                </div>

            {% else %}

                <div class="empty-message">
                    No maintenance alerts recorded yet.
                </div>

            {% endif %}


        {% elif page == "notifications" %}
            <div class="info-banner"><strong>Maintenance notifications:</strong>
                Alerts generated by the monitoring system are shown below, newest first.
                These are recorded anomaly warnings, not a live chat or confirmation of equipment failure.
            </div>
            <form method="GET" action="/" class="filter-bar" style="max-width:900px;margin-bottom:18px">
                <input type="hidden" name="page" value="notifications">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                <div class="filter-group">
                    <label for="n_severity">Severity</label>
                    <select id="n_severity" name="n_severity">
                        <option value="all">All Severities</option>
                        {% for level in ['HIGH', 'MEDIUM', 'LOW'] %}
                        <option value="{{ level }}" {% if n_severity == level %}selected{% endif %}>{{ level }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="filter-group">
                    <label for="n_sensor">Alert Type</label>
                    <select id="n_sensor" name="n_sensor">
                        <option value="all">All Sensors</option>
                        {% for sensor in sensors %}
                        <option value="{{ sensor }}" {% if n_sensor == sensor %}selected{% endif %}>{{ sensor_labels[sensor] }}</option>
                        {% endfor %}
                    </select>
                </div>
                <button type="submit" class="filter-button">Apply Filters</button>
                <a href="{{ url_for('dashboard', page='notifications', asset=selected_asset) }}" class="reset-link">Reset</a>
            </form>
            <p class="section-description">Showing {{ notification_start }}–{{ notification_end }} of {{ notification_total }} matching notifications, newest first.</p>
            <div class="notification-stream">
                {% if notification_items %}
                    {% for item in notification_items %}
                    <div class="notification-item">
                        <div class="notification-avatar" aria-hidden="true">IM</div>
                        <div class="notification-body">
                            <div class="notification-meta">Industrial Monitoring System · {{ item[1] }}</div>
                            <div class="notification-bubble {{ (item[4] or 'LOW')|lower }}">
                                <div class="notification-heading {{ item[4] }}">{{ item[4] }} — {{ sensor_labels.get(item[2], item[2]) }} Alert</div>
                                <p><strong>Machine:</strong> {{ item[6] or 'Unknown' }}</p>
                                <p><strong>Source:</strong> {{ item[7] or 'Unknown' }}</p>
                                <p><strong>Reading:</strong> {{ item[3] }} {{ item[8] or units.get(item[2], '') }}</p>
                                <p><strong>Recommended action:</strong> {{ item[5] or 'Inspect the equipment.' }}</p>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-message">No notifications match these filters.</div>
                {% endif %}
            </div>
            {% if notification_pages > 1 %}
            <div class="pagination" style="max-width:900px">
                <div class="pagination-info">Page {{ notification_page }} of {{ notification_pages }}</div>
                <div class="pagination-links">
                    {% if notification_page > 1 %}<a href="{{ url_for('dashboard', page='notifications', asset=selected_asset, n_page=notification_page-1, n_severity=n_severity, n_sensor=n_sensor) }}">Previous</a>{% endif %}
                    {% if notification_page < notification_pages %}<a href="{{ url_for('dashboard', page='notifications', asset=selected_asset, n_page=notification_page+1, n_severity=n_severity, n_sensor=n_sensor) }}">Next</a>{% endif %}
                </div>
            </div>
            {% endif %}

        {% elif page == "sensors" %}

            <div class="info-banner">
                <strong>Live sensor monitoring:</strong>
                View individual sensor readings and their recent trends.
                Graphs show up to 30 readings from one source and run. Asset: {{ latest_asset or "Unknown" }} | Source: {{ latest_source or "Unknown" }}.
            </div>

            <div class="sensor-grid">

                {% for sensor in sensors %}

                    <div class="card sensor-card">
                        <div class="card-label">
                            {{ sensor_labels[sensor] }}
                        </div>

                        <div class="sensor-value">
                            {% if latest %}
                                {{ latest[sensor] }}
                                {{ units[sensor] }}
                            {% else %}
                                --
                            {% endif %}
                        </div>

                        <div class="small-text">
                            Latest recorded reading
                        </div>
                    </div>

                {% endfor %}

            </div>

            <h2>Sensor Performance Trends</h2>

            <p class="section-description">
                Sudden spikes, drops and unusual changes may indicate
                abnormal equipment behaviour.
            </p>

            {% if timestamps %}

                <div class="graph-grid">

                    {% for sensor in sensors %}

                        <div class="graph-card">
                            <div id="{{ sensor }}" class="chart"></div>
                        </div>

                    {% endfor %}

                </div>

            {% else %}

                <div class="empty-message">
                    Graphs will appear once sensor readings are received.
                </div>

            {% endif %}


        {% elif page == "alerts" %}

            <div class="info-banner">
                <strong>Maintenance alerts:</strong>
                Review detected anomalies, their severity and the
                recommended action for each sensor.
            </div>

            <div class="summary-grid">

                <div class="card summary-card">
                    <div class="card-label">Total Alerts</div>
                    <div class="summary-number">
                        {{ alert_counts["TOTAL"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">High</div>
                    <div class="summary-number high-text">
                        {{ alert_counts["HIGH"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">Medium</div>
                    <div class="summary-number medium-text">
                        {{ alert_counts["MEDIUM"] }}
                    </div>
                </div>

                <div class="card summary-card">
                    <div class="card-label">Low</div>
                    <div class="summary-number low-text">
                        {{ alert_counts["LOW"] }}
                    </div>
                </div>

            </div>

            <h2>Filter Alerts</h2>

            <form method="GET" action="/" class="filter-bar">

                <input type="hidden" name="page" value="alerts">
                <input type="hidden" name="asset" value="{{ selected_asset }}">

                <div class="filter-group">
                    <label>Sensor</label>

                    <select name="sensor">
                        <option value="all">All Sensors</option>

                        {% for sensor in sensors %}
                            <option
                                value="{{ sensor }}"
                                {% if selected_sensor == sensor %}selected{% endif %}
                            >
                                {{ sensor_labels[sensor] }}
                            </option>
                        {% endfor %}

                    </select>
                </div>

                <div class="filter-group">
                    <label>Severity</label>

                    <select name="severity">
                        <option value="all">All Severities</option>

                        {% for level in ["HIGH", "MEDIUM", "LOW"] %}
                            <option
                                value="{{ level }}"
                                {% if selected_severity == level %}selected{% endif %}
                            >
                                {{ level }}
                            </option>
                        {% endfor %}

                    </select>
                </div>

                <div class="filter-group">
                    <label>Show Entries</label>
                    <select name="alert_limit">
                        <option value="20" {% if alert_limit == "20" %}selected{% endif %}>Latest 20</option>
                        <option value="50" {% if alert_limit == "50" %}selected{% endif %}>Latest 50</option>
                        <option value="100" {% if alert_limit == "100" %}selected{% endif %}>Latest 100</option>
                        <option value="all" {% if alert_limit == "all" %}selected{% endif %}>All Entries</option>
                    </select>
                </div>

                <button type="submit" class="filter-button">
                    Apply Filters
                </button>

                <a href="{{ url_for('dashboard', page='alerts', asset=selected_asset) }}" class="reset-link">
                    Reset
                </a>

            </form>

            <h2>Alert Results</h2>

            <p class="section-description">
                Showing {{ alerts_start }}–{{ alerts_end }} of {{ alerts_total }} matching alerts.
                {% if alert_limit == "all" %}All Entries is displayed in pages of 100 to keep the dashboard responsive.{% else %}Displaying up to {{ alert_page_size }} alerts per page.{% endif %}
            </p>

            {% if alerts %}

                <div class="table-container">
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>Sensor</th>
                            <th>Asset / Source</th>
                            <th>Reading</th>
                            <th>Z-score</th>
                            <th>Severity</th>
                            <th>Recommended Maintenance Action</th>
                        </tr>

                        {% for alert in alerts %}

                            <tr>
                                <td>{{ alert[0] }}</td>
                                <td>{{ sensor_labels.get(alert[1], alert[1]) }}</td>
                                <td>{{ alert[7] or "Unknown" }} / {{ alert[8] or "Unknown" }}</td>
                                <td>{{ alert[2] }} {{ alert[6] or units.get(alert[1], "unit unknown") }}</td>
                                <td>{{ alert[3] }}</td>
                                <td class="{{ alert[4] }}">
                                    {{ alert[4] }}
                                </td>
                                <td class="recommendation">
                                    {{ alert[5] }}
                                </td>
                            </tr>

                        {% endfor %}

                    </table>
                </div>

            {% else %}

                <div class="empty-message">
                    No alerts match the selected filters.
                </div>

            {% endif %}

            {% if alerts_total_pages > 1 %}
                <div class="pagination">
                    <div class="pagination-info">Page {{ alerts_page }} of {{ alerts_total_pages }}</div>
                    <div class="pagination-links">
                        {% if alerts_page > 1 %}
                            <a href="{{ url_for('dashboard', page='alerts', asset=selected_asset, sensor=selected_sensor, severity=selected_severity, alert_limit=alert_limit, alert_page=alerts_page-1) }}">Previous</a>
                        {% endif %}
                        <span>{{ alerts_page }} / {{ alerts_total_pages }}</span>
                        {% if alerts_page < alerts_total_pages %}
                            <a href="{{ url_for('dashboard', page='alerts', asset=selected_asset, sensor=selected_sensor, severity=selected_severity, alert_limit=alert_limit, alert_page=alerts_page+1) }}">Next</a>
                        {% endif %}
                    </div>
                </div>
            {% endif %}

            <h2>Understanding Severity</h2>

            <div class="severity-grid">

                <div class="severity-card">
                    <strong class="high-text">
                        HIGH - Immediate Attention
                    </strong>
                    <br><br>
                    Absolute Z-score of 5 or above.
                    Inspect the equipment and investigate the reading.
                </div>

                <div class="severity-card">
                    <strong class="medium-text">
                        MEDIUM - Investigate
                    </strong>
                    <br><br>
                    Absolute Z-score from 3.5 up to, but not including, 5.
                    Investigate the sensor and operating conditions.
                </div>

                <div class="severity-card">
                    <strong class="low-text">
                        LOW - Monitor
                    </strong>
                    <br><br>
                    Absolute Z-score above 1.5 but below 3.5.
                    Continue monitoring for further changes.
                </div>

            </div>


        {% elif page == "prediction" %}

            <div class="info-banner">
                <strong>AI-based machine failure prediction:</strong>
                Enter machine operating parameters to estimate the likelihood
                of failure using the trained Random Forest model.
                This model was trained on the AI4I 2020 dataset and is separate
                from the live MQTT sensor anomaly detector.
            </div>

            <h2>Machine Operating Parameters</h2>

            <p class="section-description">
                Enter the operating values for one machine. Temperature values
                are in Kelvin, speed in rpm, torque in Nm and tool wear in minutes.
            </p>

            <form method="POST" action="/?page=prediction" class="prediction-form">
                <div class="prediction-grid">

                    <div class="prediction-field">
                        <label for="air_temperature">Air Temperature (K)</label>
                        <input id="air_temperature" name="air_temperature"
                               type="number" step="any" min="250" max="350"
                               value="{{ prediction_input.get('air_temperature', '300') }}" required>
                    </div>

                    <div class="prediction-field">
                        <label for="process_temperature">Process Temperature (K)</label>
                        <input id="process_temperature" name="process_temperature"
                               type="number" step="any" min="250" max="400"
                               value="{{ prediction_input.get('process_temperature', '310') }}" required>
                    </div>

                    <div class="prediction-field">
                        <label for="rotational_speed">Rotational Speed (rpm)</label>
                        <input id="rotational_speed" name="rotational_speed"
                               type="number" step="any" min="100" max="5000"
                               value="{{ prediction_input.get('rotational_speed', '1500') }}" required>
                    </div>

                    <div class="prediction-field">
                        <label for="torque">Torque (Nm)</label>
                        <input id="torque" name="torque"
                               type="number" step="any" min="0" max="100"
                               value="{{ prediction_input.get('torque', '40') }}" required>
                    </div>

                    <div class="prediction-field">
                        <label for="tool_wear">Tool Wear (minutes)</label>
                        <input id="tool_wear" name="tool_wear"
                               type="number" step="any" min="0" max="300"
                               value="{{ prediction_input.get('tool_wear', '100') }}" required>
                    </div>

                    <div class="prediction-field">
                        <label for="machine_type">Machine Type</label>
                        <select id="machine_type" name="machine_type" required>
                            <option value="L" {% if prediction_input.get('machine_type', 'L') == 'L' %}selected{% endif %}>L</option>
                            <option value="M" {% if prediction_input.get('machine_type') == 'M' %}selected{% endif %}>M</option>
                            <option value="H" {% if prediction_input.get('machine_type') == 'H' %}selected{% endif %}>H</option>
                        </select>
                    </div>

                </div>

                <button type="submit" class="prediction-submit">
                    Predict Machine Failure
                </button>
            </form>

            {% if prediction_result %}
                <div class="prediction-result {{ 'failure' if prediction_result.prediction == 1 else 'normal' }}">
                    <h2 style="margin-top: 0;">
                        {% if prediction_result.prediction == 1 %}
                            Failure Risk Detected
                        {% else %}
                            No Failure Detected
                        {% endif %}
                    </h2>

                    <p>
                        <strong>Model output:</strong>
                        {{ 'Machine failure predicted' if prediction_result.prediction == 1 else 'Machine predicted as normal' }}
                    </p>

                    <p>
                        <strong>Failure score:</strong>
                        {{ prediction_result.score }}%
                    </p>

                    <p class="small-text">
                        The score represents the proportion of Random Forest trees
                        voting for failure. It is a model score, not a calibrated
                        real-world probability or a guarantee of failure.
                    </p>
                </div>
            {% endif %}

            {% if prediction_error %}
                <div class="prediction-error">{{ prediction_error }}</div>
            {% endif %}

            <h2>About This Model</h2>
            <div class="detail-grid">
                <div class="detail-card">
                    <div class="card-label">Algorithm</div>
                    <div class="detail-value">Random Forest Classifier</div>
                </div>
                <div class="detail-card">
                    <div class="card-label">Training Dataset</div>
                    <div class="detail-value">AI4I 2020 Predictive Maintenance</div>
                </div>
                <div class="detail-card">
                    <div class="card-label">Held-out Test Accuracy</div>
                    <div class="detail-value">97.80%</div>
                </div>
                <div class="detail-card">
                    <div class="card-label">Held-out Test F1 Score</div>
                    <div class="detail-value">65.26%</div>
                </div>
            </div>

            <p class="section-description" style="margin-top: 15px;">
                The AI4I dataset is synthetic. Model performance on this dataset
                does not guarantee the same performance on real industrial equipment.
            </p>


        {% elif page == "ai4i_replay" %}

            <div class="info-banner">
                <strong>Replay prediction results:</strong>
                This page displays machine-failure predictions generated when
                records from the AI4I 2020 dataset are replayed through MQTT.
                These are simulated dataset records, not readings from physical
                factory equipment. The actual outcome is available because the
                replay dataset includes a known failure label.
            </div>

            <h2>Latest Replay Performance</h2>

            <p class="section-description">
                These metrics cover only the most recent tracked replay run, identified by its unique run ID.
                The timestamps below show the replay interval.
            </p>

            <div class="summary-grid">
                <div class="card summary-card">
                    <div class="card-label">Latest Run Records</div>
                    <div class="summary-number">{{ latest_prediction_metrics["total"] }}</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Latest Run Accuracy</div>
                    <div class="summary-number">{{ latest_prediction_metrics["accuracy"] }}%</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Correct Predictions</div>
                    <div class="summary-number normal-text">{{ latest_prediction_metrics["correct"] }}</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Incorrect Predictions</div>
                    <div class="summary-number high-text">{{ latest_prediction_metrics["incorrect"] }}</div>
                </div>
            </div>

            <p class="section-description" style="margin-top: 12px;">
                Run ID: {{ latest_run_id or "Not available" }}. <br>Replay interval: {{ latest_prediction_metrics["start_timestamp"] or "Not available" }}
                to {{ latest_prediction_metrics["end_timestamp"] or "Not available" }}.
            </p>

            <h2>Latest Replay Confusion Matrix</h2>

            <div class="summary-grid">
                <div class="card summary-card">
                    <div class="card-label">True Positives</div>
                    <div class="summary-number">{{ latest_prediction_metrics["true_positives"] }}</div>
                    <div class="small-text">Failure correctly predicted</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">False Positives</div>
                    <div class="summary-number high-text">{{ latest_prediction_metrics["false_positives"] }}</div>
                    <div class="small-text">Normal record predicted as failure</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">False Negatives</div>
                    <div class="summary-number high-text">{{ latest_prediction_metrics["false_negatives"] }}</div>
                    <div class="small-text">Failure missed by the model</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">True Negatives</div>
                    <div class="summary-number">{{ latest_prediction_metrics["true_negatives"] }}</div>
                    <div class="small-text">Normal record correctly predicted</div>
                </div>
            </div>

            <h2>Overall Replay Performance (All Runs)</h2>

            <p class="section-description">
                Results combine tracked runs and {{ legacy_prediction_count }} historical records without a run ID. Repeated records are not independent model tests.
            </p>

            <div class="summary-grid">
                <div class="card summary-card">
                    <div class="card-label">Total Replay Records</div>
                    <div class="summary-number">{{ prediction_metrics["total"] }}</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Replay Accuracy</div>
                    <div class="summary-number">{{ prediction_metrics["accuracy"] }}%</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Correct Predictions</div>
                    <div class="summary-number normal-text">{{ prediction_metrics["correct"] }}</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">Incorrect Predictions</div>
                    <div class="summary-number high-text">{{ prediction_metrics["incorrect"] }}</div>
                </div>
            </div>

            <h2>Overall Confusion Matrix (All Runs)</h2>

            <div class="summary-grid">
                <div class="card summary-card">
                    <div class="card-label">True Positives</div>
                    <div class="summary-number">{{ prediction_metrics["true_positives"] }}</div>
                    <div class="small-text">Failure correctly predicted</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">False Positives</div>
                    <div class="summary-number high-text">{{ prediction_metrics["false_positives"] }}</div>
                    <div class="small-text">Normal record predicted as failure</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">False Negatives</div>
                    <div class="summary-number high-text">{{ prediction_metrics["false_negatives"] }}</div>
                    <div class="small-text">Failure missed by the model</div>
                </div>
                <div class="card summary-card">
                    <div class="card-label">True Negatives</div>
                    <div class="summary-number">{{ prediction_metrics["true_negatives"] }}</div>
                    <div class="small-text">Normal record correctly predicted</div>
                </div>
            </div>

            <h2>All Replay Prediction History</h2>

            <p class="section-description">
                This table contains records from all replay runs, newest first.
            </p>

            <form method="GET" action="/" class="filter-bar">
                <input type="hidden" name="page" value="ai4i_replay">
                <div class="filter-group">
                    <label>Show Entries</label>
                    <select name="prediction_limit">
                        <option value="20" {% if prediction_limit == "20" %}selected{% endif %}>Latest 20</option>
                        <option value="50" {% if prediction_limit == "50" %}selected{% endif %}>Latest 50</option>
                        <option value="100" {% if prediction_limit == "100" %}selected{% endif %}>Latest 100</option>
                        <option value="all" {% if prediction_limit == "all" %}selected{% endif %}>All Entries</option>
                    </select>
                </div>
                <button type="submit" class="filter-button">Show Records</button>
            </form>

            <p class="section-description" style="margin-top: 15px;">
                Showing {{ predictions_start }}–{{ predictions_end }} of {{ predictions_total }} records, newest first.
                {% if prediction_limit == "all" %}All Entries is displayed in pages of 100 to keep the dashboard responsive.{% else %}Displaying up to {{ predictions_page_size }} records per page.{% endif %}
            </p>

            {% if prediction_history %}
                <div class="table-container">
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>UDI</th>
                            <th>Product ID</th>
                            <th>Run ID</th>
                            <th>Machine Type</th>
                            <th>Failure Score</th>
                            <th>Threshold</th>
                            <th>Predicted</th>
                            <th>Actual</th>
                            <th>Result</th>
                        </tr>
                        {% for record in prediction_history %}
                            <tr>
                                <td>{{ record[0] }}</td>
                                <td>{{ record[1] }}</td>
                                <td>{{ record[2] }}</td>
                                <td style="overflow-wrap:anywhere;max-width:180px">{{ record[9] or "Legacy / untracked" }}</td>
                                <td>{{ record[3] }}</td>
                                <td>{{ "%.2f"|format(record[4] * 100) }}%</td>
                                <td>{{ "%.2f"|format(record[5] * 100) }}%</td>
                                <td class="{{ 'failure-text' if record[6] == 1 else 'normal-text' }}">
                                    {{ "FAILURE" if record[6] == 1 else "NORMAL" }}
                                </td>
                                <td class="{{ 'failure-text' if record[7] == 1 else 'normal-text' }}">
                                    {{ "FAILURE" if record[7] == 1 else "NORMAL" }}
                                </td>
                                <td class="{{ 'correct-text' if record[8] == 1 else 'incorrect-text' }}">
                                    {{ "CORRECT" if record[8] == 1 else "INCORRECT" }}
                                </td>
                            </tr>
                        {% endfor %}
                    </table>
                </div>
            {% else %}
                <div class="empty-message">
                    No replay predictions are available yet. Start the MQTT consumer,
                    then run messaging/ai4i_replay_publisher.py to send dataset records.
                </div>
            {% endif %}

            {% if predictions_total_pages > 1 %}
                <div class="pagination">
                    <div class="pagination-info">Page {{ predictions_page }} of {{ predictions_total_pages }}</div>
                    <div class="pagination-links">
                        {% if predictions_page > 1 %}
                            <a href="{{ url_for('dashboard', page='ai4i_replay', prediction_limit=prediction_limit, prediction_page=predictions_page-1) }}">Previous</a>
                        {% endif %}
                        <span>{{ predictions_page }} / {{ predictions_total_pages }}</span>
                        {% if predictions_page < predictions_total_pages %}
                            <a href="{{ url_for('dashboard', page='ai4i_replay', prediction_limit=prediction_limit, prediction_page=predictions_page+1) }}">Next</a>
                        {% endif %}
                    </div>
                </div>
            {% endif %}

            <p class="section-description" style="margin-top: 15px;">
                The failure score is the proportion of Random Forest trees voting for failure;
                it is not a calibrated real-world probability. Replay accuracy describes only
                the records currently stored from the AI4I dataset and is not the model's held-out test accuracy.
            </p>


        {% elif page == "maintenance" %}
            <div class="info-banner"><strong>Maintenance management:</strong>
                Acknowledge sensor alerts, assign planned maintenance, and record completed work.
                Acknowledgement means an operator has reviewed an alert; it does not confirm a repair.
            </div>
            {% if maintenance_notice %}<div class="maintenance-success">{{ maintenance_notice }}</div>{% endif %}
            {% if maintenance_error %}<div class="maintenance-error">{{ maintenance_error }}</div>{% endif %}

            <h2>Schedule Maintenance</h2>
            <form method="POST" action="{{ url_for('maintenance_action') }}" class="prediction-form maintenance-form">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                <input type="hidden" name="action" value="schedule">
                <input name="asset_id" maxlength="100" placeholder="Asset ID" required aria-label="Asset ID">
                <input name="assigned_to" maxlength="80" placeholder="Assigned engineer" required aria-label="Assigned engineer">
                <select name="priority" aria-label="Priority"><option>HIGH</option><option selected>MEDIUM</option><option>LOW</option></select>
                <input type="datetime-local" name="scheduled_for" required aria-label="Scheduled time">
                <textarea name="description" maxlength="1000" placeholder="Maintenance task" required aria-label="Maintenance task"></textarea>
                <button type="submit" class="filter-button">Schedule Task</button>
                <div class="maintenance-note">Enter the scheduled date and time in the factory's local time zone.</div>
            </form>


            <h2>Review Alerts</h2>
            <p class="section-description">Filter historical alerts and acknowledge those requiring review. Acknowledgement does not mean maintenance is complete.</p>
            <form method="GET" action="/" class="filter-bar">
                <input type="hidden" name="page" value="maintenance">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                <div class="filter-group"><label for="m_severity">Severity</label>
                    <select id="m_severity" name="m_severity">
                        <option value="all" {% if m_severity == 'all' %}selected{% endif %}>All Severities</option>
                        {% for level in ['HIGH','MEDIUM','LOW'] %}<option value="{{ level }}" {% if m_severity == level %}selected{% endif %}>{{ level }}</option>{% endfor %}
                    </select>
                </div>
                <div class="filter-group"><label for="m_status">Review Status</label>
                    <select id="m_status" name="m_status">
                        <option value="all" {% if m_status == 'all' %}selected{% endif %}>All Alerts</option>
                        <option value="unacknowledged" {% if m_status == 'unacknowledged' %}selected{% endif %}>Unacknowledged</option>
                        <option value="acknowledged" {% if m_status == 'acknowledged' %}selected{% endif %}>Acknowledged</option>
                    </select>
                </div>
                <div class="filter-group"><label for="m_limit">Show Entries</label>
                    <select id="m_limit" name="m_limit">
                        {% for option in ['20','50','100','all'] %}
                        <option value="{{ option }}" {% if m_limit == option %}selected{% endif %}>{{ 'All Entries (paginated)' if option == 'all' else 'Latest ' + option }}</option>
                        {% endfor %}
                    </select>
                </div>
                <button type="submit" class="filter-button">Apply Filters</button>
                <a href="{{ url_for('dashboard', page='maintenance', asset=selected_asset) }}" class="reset-link">Reset</a>
            </form>
            <p class="section-description" style="margin-top:15px">Showing {{ m_start }}–{{ m_end }} of {{ m_total }} matching alerts. Page {{ m_page }} of {{ m_pages }}.</p>
            {% if maintenance_alerts %}
            <div class="table-container"><table>
                <tr><th>Time</th><th>Asset / Source</th><th>Sensor</th><th>Severity</th><th>Review Status</th><th>Action</th></tr>
                {% for alert in maintenance_alerts %}
                <tr>
                    <td>{{ alert[1] }}</td><td>{{ alert[4] or "Unknown" }} / {{ alert[5] or "Unknown" }}</td>
                    <td>{{ sensor_labels.get(alert[2], alert[2]) }}</td>
                    <td class="{{ alert[3] }}">{{ alert[3] }}</td>
                    <td>{{ "Acknowledged by " + alert[6] if alert[6] else "Unacknowledged" }}</td>
                    <td>
                        {% if not alert[6] %}
                        <form method="POST" action="{{ url_for('maintenance_action') }}" class="maintenance-form">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                            <input type="hidden" name="action" value="acknowledge">
                            <input type="hidden" name="alert_id" value="{{ alert[0] }}">
                            <input name="operator" maxlength="80" placeholder="Operator name" required aria-label="Operator name">
                            <button type="submit" class="filter-button">Acknowledge</button>
                        </form>
                        {% else %}<span class="small-text">{{ alert[7] }}</span>{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table></div>
            {% else %}<div class="empty-message">No alerts match the selected filters.</div>{% endif %}
            {% if m_pages > 1 %}
            <div class="pagination"><div class="pagination-info">Page {{ m_page }} of {{ m_pages }}</div>
                <div class="pagination-links">
                    {% if m_page > 1 %}<a href="{{ url_for('dashboard', page='maintenance', asset=selected_asset, m_severity=m_severity, m_status=m_status, m_limit=m_limit, m_page=m_page-1) }}">Previous</a>{% endif %}
                    <span>{{ m_page }} / {{ m_pages }}</span>
                    {% if m_page < m_pages %}<a href="{{ url_for('dashboard', page='maintenance', asset=selected_asset, m_severity=m_severity, m_status=m_status, m_limit=m_limit, m_page=m_page+1) }}">Next</a>{% endif %}
                </div>
            </div>
            {% endif %}

            <h2>Maintenance Tasks and History</h2>
            {% if maintenance_tasks %}
            <div class="table-container"><table>
                <tr><th>Created (UTC)</th><th>Asset</th><th>Priority</th><th>Engineer</th><th>Scheduled (local)</th><th>Description</th><th>Status</th><th>Action</th></tr>
                {% for task in maintenance_tasks %}
                <tr>
                    <td>{{ task[1] }}</td><td>{{ task[2] }}</td><td class="{{ task[3] }}">{{ task[3] }}</td>
                    <td>{{ task[4] }}</td><td>{{ task[5] }}</td><td class="recommendation">{{ task[6] }}</td>
                    <td>{{ task[7] }}{% if task[8] %}<div class="small-text">Completed: {{ task[8] }}</div>{% endif %}</td>
                    <td>{% if task[7] == 'SCHEDULED' %}
                        <form method="POST" action="{{ url_for('maintenance_action') }}" class="maintenance-form">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                            <input type="hidden" name="action" value="complete">
                            <input type="hidden" name="task_id" value="{{ task[0] }}">
                            <input name="completion_notes" maxlength="1000" placeholder="Work performed" required aria-label="Work performed">
                            <button type="submit" class="filter-button">Mark Complete</button>
                        </form>
                    {% else %}<span class="small-text">{{ task[9] or 'No notes' }}</span>{% endif %}</td>
                </tr>
                {% endfor %}
            </table></div>
            {% else %}<div class="empty-message">No maintenance tasks have been scheduled.</div>{% endif %}
            <p class="maintenance-note">Showing the latest 100 tasks. Work records are operator-entered and are not automatically verified against physical equipment.</p>

        {% elif page == "history" %}

            <div class="info-banner">
                <strong>Sensor reading history:</strong>
                Review the latest readings stored by the monitoring system.
            </div>

            <h2>Latest Sensor Readings</h2>

            <form method="GET" action="/" class="filter-bar">
                <input type="hidden" name="page" value="history">
                <input type="hidden" name="asset" value="{{ selected_asset }}">
                <div class="filter-group">
                    <label>Show Entries</label>
                    <select name="history_limit">
                        <option value="20" {% if history_limit == "20" %}selected{% endif %}>Latest 20</option>
                        <option value="50" {% if history_limit == "50" %}selected{% endif %}>Latest 50</option>
                        <option value="100" {% if history_limit == "100" %}selected{% endif %}>Latest 100</option>
                        <option value="all" {% if history_limit == "all" %}selected{% endif %}>All Entries</option>
                    </select>
                </div>
                <button type="submit" class="filter-button">Show Records</button>
            </form>

            <p class="section-description" style="margin-top: 15px;">
                Showing {{ readings_start }}–{{ readings_end }} of {{ readings_total }} records, newest first.
                {% if history_limit == "all" %}All Entries is displayed in pages of 100 to keep the dashboard responsive.{% else %}Displaying up to {{ history_page_size }} records per page.{% endif %}
            </p>

            {% if readings %}

                <div class="table-container">
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>Asset</th><th>Source</th>
                            <th>Temperature</th><th>Vibration</th><th>Humidity</th><th>Pressure</th><th>Current</th>
                        </tr>

                        {% for row in readings %}

                            <tr>
                                {% for value in row %}
                                    <td>{{ value }}</td>
                                {% endfor %}
                            </tr>

                        {% endfor %}

                    </table>
                </div>

            {% else %}

                <div class="empty-message">
                    No sensor readings are available.
                </div>

            {% endif %}

            {% if readings_total_pages > 1 %}
                <div class="pagination">
                    <div class="pagination-info">Page {{ readings_page }} of {{ readings_total_pages }}</div>
                    <div class="pagination-links">
                        {% if readings_page > 1 %}
                            <a href="{{ url_for('dashboard', page='history', asset=selected_asset, history_limit=history_limit, history_page=readings_page-1) }}">Previous</a>
                        {% endif %}
                        <span>{{ readings_page }} / {{ readings_total_pages }}</span>
                        {% if readings_page < readings_total_pages %}
                            <a href="{{ url_for('dashboard', page='history', asset=selected_asset, history_limit=history_limit, history_page=readings_page+1) }}">Next</a>
                        {% endif %}
                    </div>
                </div>
            {% endif %}

        {% endif %}


        <div class="footer">
            IoT Sensor Network for Predictive Maintenance
            <br>
            Automated Monitoring | Anomaly Detection | Maintenance Recommendations
        </div>

    </main>


    <!-- PLOTLY CHARTS -->

    {% if page == "sensors" and timestamps %}

    <script>

        const timestamps = {{ timestamps | tojson }};
        const sensorData = {{ sensor_data | tojson }};
        const units = {{ units | tojson }};

        const titles = {
            temperature: "Temperature",
            vibration: "Vibration",
            humidity: "Humidity",
            pressure: "Pressure",
            current: "Current"
        };

        for (const sensor of Object.keys(titles)) {

            const trace = {
                x: timestamps,
                y: sensorData[sensor],
                type: "scatter",
                mode: "lines+markers",
                name: titles[sensor],

                line: {
                    width: 2
                },

                marker: {
                    size: 6
                },

                hovertemplate:
                    "<b>" + titles[sensor] + "</b><br>" +
                    "Time: %{x}<br>" +
                    "Reading: %{y:.2f} " + units[sensor] +
                    "<extra></extra>"
            };

            const layout = {

                title: {
                    text: titles[sensor] + " (" + units[sensor] + ")",
                    font: { size: 16 }
                },

                xaxis: {
                    title: "Time",
                    type: "date",
                    tickformat: "%H:%M:%S",
                    nticks: 5,
                    automargin: true
                },

                yaxis: {
                    title: "Reading (" + units[sensor] + ")",
                    automargin: true
                },

                margin: {
                    t: 55,
                    l: 65,
                    r: 20,
                    b: 65
                },

                paper_bgcolor: "white",
                plot_bgcolor: "white",
                showlegend: false
            };

            Plotly.newPlot(
                sensor,
                [trace],
                layout,
                {
                    responsive: true,
                    displayModeBar: false
                }
            );
        }

    </script>

    {% endif %}

</body>
</html>
"""



def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def create_maintenance_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_acknowledgements (
            alert_id INTEGER PRIMARY KEY,
            operator TEXT NOT NULL,
            acknowledged_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            scheduled_for TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'SCHEDULED',
            completed_at TEXT,
            completion_notes TEXT
        )
    """)


def maintenance_csrf_token():
    if "maintenance_csrf" not in session:
        session["maintenance_csrf"] = secrets.token_hex(32)
    return session["maintenance_csrf"]



# Dashboard authentication
@app.before_request
def require_dashboard_login():
    if request.endpoint in ("dashboard_login", "dashboard_logout"):
        return None
    if not session.get("authenticated"):
        return redirect(url_for("dashboard_login"))
    return None


@app.route("/login", methods=["GET", "POST"])
def dashboard_login():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        expected_user = os.environ.get("DASHBOARD_USERNAME", "")
        expected_password = os.environ.get("DASHBOARD_PASSWORD", "")

        supplied_user = request.form.get("username", "")
        supplied_password = request.form.get("password", "")

        if (
            expected_user
            and expected_password
            and hmac.compare_digest(supplied_user, expected_user)
            and hmac.compare_digest(supplied_password, expected_password)
        ):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("dashboard"))

        error = "Invalid username or password."

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign In | Predictive Maintenance</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f7f8f2;
    color: #243b30;
}
.layout {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1.1fr 1fr;
}
.hero {
    background: linear-gradient(145deg, #183d30, #376d51);
    color: #fff;
    padding: 65px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.brand {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: .4px;
}
.hero-content { max-width: 540px; }
.hero h1 {
    font-size: clamp(34px, 4vw, 58px);
    line-height: 1.12;
    letter-spacing: -1.5px;
    margin-bottom: 20px;
}
.hero p {
    font-size: 17px;
    line-height: 1.8;
    color: #dce9df;
}
.features {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 35px;
}
.feature {
    border: 1px solid #ffffff40;
    border-radius: 30px;
    padding: 10px 15px;
    font-size: 13px;
}
.hero-footer {
    font-size: 12px;
    color: #c6dbce;
}
.login-side {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 35px;
}
.login-card {
    width: 100%;
    max-width: 400px;
    animation: appear .5s ease-out both;
}
.eyebrow {
    color: #4e8265;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1.6px;
}
.login-card h2 {
    font-size: 34px;
    margin: 12px 0;
    letter-spacing: -1px;
}
.subtitle {
    color: #728078;
    line-height: 1.6;
    margin-bottom: 35px;
}
label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    margin: 20px 0 9px;
}
input {
    width: 100%;
    padding: 14px 15px;
    border: 1px solid #d8e0d9;
    border-radius: 9px;
    background: #fff;
    color: #243b30;
    font: inherit;
    outline: none;
    transition: border-color .2s, box-shadow .2s;
}
input:focus {
    border-color: #3b8059;
    box-shadow: 0 0 0 3px #3b80591c;
}
.password-wrap { position: relative; }
.password-wrap input { padding-right: 75px; }
.toggle {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    border: none;
    background: transparent;
    color: #397653;
    cursor: pointer;
    font-weight: 600;
}
.submit {
    margin-top: 28px;
    width: 100%;
    padding: 15px;
    border: 0;
    border-radius: 9px;
    background: #285b40;
    color: white;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    transition: background .2s, transform .2s;
}
.submit:hover {
    background: #1d4631;
    transform: translateY(-1px);
}
.error {
    background: #fff0ee;
    border: 1px solid #f3c6c0;
    color: #9b3027;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 18px;
}
.secure-note {
    text-align: center;
    color: #87938b;
    font-size: 12px;
    margin-top: 25px;
}
@keyframes appear {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 800px) {
    .layout { grid-template-columns: 1fr; }
    .hero { padding: 30px; gap: 20px; }
    .hero h1 { font-size: 30px; }
    .hero-content p, .features, .hero-footer { display: none; }
    .login-side { padding: 45px 25px; }
}
@media (prefers-reduced-motion: reduce) {
    .login-card { animation: none; }
    .submit { transition: none; }
}

.machine-visual {
    width: 100%;
    max-width: 540px;
    margin-top: 28px;
}
.machine-visual svg {
    width: 100%;
    height: auto;
    display: block;
}
.signal-dot {
    animation: signalPulse 2.2s ease-in-out infinite;
}
.signal-line {
    stroke-dasharray: 360;
    stroke-dashoffset: 360;
    animation: drawSignal 4s ease-in-out infinite;
}
.connection {
    animation: flowSignal 6s linear infinite;
}
@keyframes signalPulse {
    0%, 100% { opacity: .45; }
    50% { opacity: 1; }
}
@keyframes drawSignal {
    0% { stroke-dashoffset: 360; opacity: .4; }
    45%, 85% { stroke-dashoffset: 0; opacity: 1; }
    100% { stroke-dashoffset: 0; opacity: .4; }
}
@keyframes flowSignal {
    to { stroke-dashoffset: -120; }
}
@media (prefers-reduced-motion: reduce) {
    .signal-dot, .signal-line, .connection {
        animation: none;
    }
    .signal-line {
        stroke-dashoffset: 0;
    }
}
</style>
</head>
<body>
<div class="layout">
    <section class="hero">
        <div class="brand">INDUSTRIAL INTELLIGENCE</div>
        <div class="hero-content">
            <h1>Smarter monitoring.<br>Better maintenance.</h1>
            <p>
                Monitor equipment conditions, identify unusual
                behaviour and manage maintenance activities
                from one integrated platform.
            </p>

            <div class="machine-visual" aria-label="Illustration of an industrial motor with live sensor signals">
                <svg viewBox="0 0 540 290" role="img"
                     aria-label="Industrial motor monitoring illustration">
                    <defs>
                        <linearGradient id="motorGradient" x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0%" stop-color="#a5cbb0"/>
                            <stop offset="100%" stop-color="#568d72"/>
                        </linearGradient>
                        <linearGradient id="screenGradient" x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0%" stop-color="#214c3c"/>
                            <stop offset="100%" stop-color="#153a2d"/>
                        </linearGradient>
                    </defs>

                    <!-- Background grid -->
                    <g stroke="#ffffff" stroke-opacity=".09">
                        <path d="M0 50 H540 M0 100 H540 M0 150 H540 M0 200 H540 M0 250 H540"/>
                        <path d="M50 0 V290 M110 0 V290 M170 0 V290 M230 0 V290 M290 0 V290 M350 0 V290 M410 0 V290 M470 0 V290"/>
                    </g>

                    <!-- Monitoring panel -->
                    <rect x="315" y="58" width="193" height="152" rx="15"
                          fill="url(#screenGradient)" stroke="#8ebda0"
                          stroke-opacity=".55"/>
                    <circle cx="334" cy="78" r="4" fill="#a6e7b9" class="signal-dot"/>
                    <text x="347" y="82" fill="#e4f2e7" font-size="11"
                          font-family="Arial">SENSOR SIGNAL</text>
                    <path d="M330 155 H492" stroke="#8ebda0" stroke-opacity=".3"/>
                    <path d="M330 125 H492" stroke="#8ebda0" stroke-opacity=".2"/>
                    <path d="M330 185 H492" stroke="#8ebda0" stroke-opacity=".2"/>
                    <path class="signal-line"
                          d="M330 155 L350 155 L365 135 L381 168 L398 113 L415 148 L433 139 L450 158 L467 121 L492 139"
                          fill="none" stroke="#b8f0c6" stroke-width="3"
                          stroke-linecap="round" stroke-linejoin="round"/>
                    <text x="331" y="198" fill="#a9cdb6" font-size="10"
                          font-family="Arial">LIVE TELEMETRY</text>

                    <!-- Industrial motor base -->
                    <rect x="49" y="214" width="215" height="15" rx="5"
                          fill="#aac9b4" opacity=".85"/>
                    <rect x="72" y="227" width="30" height="12" rx="3"
                          fill="#7fab90"/>
                    <rect x="205" y="227" width="30" height="12" rx="3"
                          fill="#7fab90"/>

                    <!-- Motor body -->
                    <rect x="85" y="112" width="144" height="105" rx="22"
                          fill="url(#motorGradient)" stroke="#c9e8d0"
                          stroke-width="2"/>
                    <g stroke="#2e654c" stroke-opacity=".45" stroke-width="5">
                        <path d="M112 122 V206 M131 119 V210 M150 119 V210 M169 119 V210 M188 122 V206"/>
                    </g>
                    <rect x="111" y="95" width="76" height="22" rx="7"
                          fill="#8ebca0" stroke="#c6e7ce"/>
                    <circle cx="229" cy="164" r="44" fill="#2b604a"
                            stroke="#c5e7cf" stroke-width="3"/>
                    <circle cx="229" cy="164" r="28" fill="#78aa89"/>
                    <circle cx="229" cy="164" r="17" fill="#d2ebd6"/>
                    <circle cx="229" cy="164" r="6" fill="#285b43"/>
                    <rect x="266" y="157" width="40" height="14" rx="5"
                          fill="#c2e2ca"/>

                    <!-- Sensor nodes -->
                    <circle cx="112" cy="94" r="7" fill="#c0f5c8"
                            class="signal-dot"/>
                    <circle cx="229" cy="119" r="7" fill="#c0f5c8"
                            class="signal-dot"/>
                    <circle cx="273" cy="210" r="7" fill="#c0f5c8"
                            class="signal-dot"/>

                    <!-- Connection paths -->
                    <path class="connection"
                          d="M112 94 V49 H300 Q315 49 315 64"
                          fill="none" stroke="#a9dfb9" stroke-width="2"
                          stroke-dasharray="5 7"/>
                    <path class="connection"
                          d="M229 119 V80 H300"
                          fill="none" stroke="#a9dfb9" stroke-width="2"
                          stroke-dasharray="5 7"/>
                    <path class="connection"
                          d="M273 210 H300 Q315 210 315 195"
                          fill="none" stroke="#a9dfb9" stroke-width="2"
                          stroke-dasharray="5 7"/>

                    <!-- Status -->
                    <circle cx="83" cy="265" r="5" fill="#a6e7b9"
                            class="signal-dot"/>
                    <text x="97" y="269" fill="#dce9df" font-size="12"
                          font-family="Arial">Equipment monitoring</text>
                </svg>
            </div>
        </div>
        <div class="hero-footer">
            IoT-Based Predictive Maintenance System
        </div>
    </section>

    <main class="login-side">
        <div class="login-card">
            <div class="eyebrow">WELCOME BACK</div>
            <h2>Sign in</h2>
            <p class="subtitle">
                Access your equipment monitoring dashboard.
            </p>

            {% if error %}
            <div class="error" role="alert">{{ error }}</div>
            {% endif %}

            <form method="POST">
                <label for="username">Username</label>
                <input id="username" name="username"
                       autocomplete="username"
                       placeholder="Enter your username"
                       required autofocus>

                <label for="password">Password</label>
                <div class="password-wrap">
                    <input id="password" name="password"
                           type="password"
                           autocomplete="current-password"
                           placeholder="Enter your password" required>
                    <button class="toggle" type="button"
                            onclick="togglePassword()" id="toggleBtn">
                        Show
                    </button>
                </div>

                <button class="submit" type="submit">
                    Sign in to Dashboard
                </button>
            </form>

            <p class="secure-note">
                Authorised personnel access only
            </p>
        </div>
    </main>
</div>
<script>
function togglePassword() {
    const input = document.getElementById('password');
    const button = document.getElementById('toggleBtn');
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.textContent = visible ? 'Hide' : 'Show';
}
</script>
</body>
</html>
""", error=error)


@app.route("/logout", methods=["POST"])
def dashboard_logout():
    session.clear()
    return redirect(url_for("dashboard_login"))

@app.route("/maintenance/action", methods=["POST"])
def maintenance_action():
    if not secrets.compare_digest(request.form.get("csrf_token", ""), maintenance_csrf_token()):
        abort(400, "Invalid form token")

    action = request.form.get("action", "")
    notice = None
    error = None
    with sqlite3.connect(DB_PATH) as conn:
        create_maintenance_tables(conn)
        if action == "acknowledge":
            try:
                alert_id = int(request.form.get("alert_id", ""))
            except ValueError:
                abort(400, "Invalid alert ID")
            operator = request.form.get("operator", "").strip()
            if not (0 < len(operator) <= 80):
                error = "Enter a valid operator name."
            elif not conn.execute("SELECT 1 FROM alerts WHERE id = ?", (alert_id,)).fetchone():
                error = "Alert not found."
            else:
                result = conn.execute("""
                    INSERT OR IGNORE INTO alert_acknowledgements
                    (alert_id, operator, acknowledged_at) VALUES (?, ?, ?)
                """, (alert_id, operator, utc_timestamp()))
                notice = "Alert acknowledged." if result.rowcount else "Alert was already acknowledged."
        elif action == "schedule":
            asset = request.form.get("asset_id", "").strip()
            engineer = request.form.get("assigned_to", "").strip()
            priority = request.form.get("priority", "")
            scheduled = request.form.get("scheduled_for", "").strip()
            description = request.form.get("description", "").strip()
            try:
                datetime.fromisoformat(scheduled)
                valid_date = True
            except ValueError:
                valid_date = False
            if not (0 < len(asset) <= 100 and 0 < len(engineer) <= 80 and
                    0 < len(description) <= 1000 and priority in ("HIGH", "MEDIUM", "LOW") and valid_date):
                error = "Check the maintenance task fields and try again."
            else:
                conn.execute("""
                    INSERT INTO maintenance_tasks
                    (created_at, asset_id, priority, assigned_to, scheduled_for, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED')
                """, (utc_timestamp(), asset, priority, engineer, scheduled, description))
                notice = "Maintenance task scheduled."
        elif action == "complete":
            try:
                task_id = int(request.form.get("task_id", ""))
            except ValueError:
                abort(400, "Invalid task ID")
            notes = request.form.get("completion_notes", "").strip()
            if not (0 < len(notes) <= 1000):
                error = "Enter the work performed."
            else:
                result = conn.execute("""
                    UPDATE maintenance_tasks
                    SET status = 'COMPLETED', completed_at = ?, completion_notes = ?
                    WHERE id = ? AND status = 'SCHEDULED'
                """, (utc_timestamp(), notes, task_id))
                if result.rowcount:
                    notice = "Maintenance task marked complete."
                else:
                    error = "Task not found or already completed."
        else:
            abort(400, "Unknown maintenance action")
    return redirect(url_for("dashboard", page="maintenance", asset=request.form.get("asset", "all"), notice=notice, error=error), code=303)


@app.route("/", methods=["GET", "POST"])
def dashboard():

    page = request.args.get("page", "overview")

    valid_pages = [item[0] for item in PAGES]

    if page not in valid_pages:
        page = "overview"

    page_details = {
        "overview": (
            "Overview",
            "A quick view of equipment readings and maintenance alerts."
        ),
        "sensors": (
            "Live Sensors",
            "Monitor individual sensor readings and performance trends."
        ),
        "alerts": (
            "Maintenance Alerts",
            "Review unusual readings and recommended maintenance actions."
        ),
        "history": (
            "Reading History",
            "Review recently stored sensor readings."
        ),
        "prediction": (
            "Machine Failure Prediction",
            "Estimate machine failure risk using the trained Random Forest model."
        ),
        "maintenance": ("Maintenance Management", "Acknowledge alerts and manage maintenance work."),
        "notifications": ("Maintenance Notifications", "View recorded alerts in a conversation-style feed."),
        "ai4i_replay": (
            "Machine Failure Prediction – Replay Results",
            "Review machine-failure predictions generated from replayed machine-operation records."
        )

    }

    page_title, page_description = page_details[page]

    prediction_result = None
    prediction_error = None
    prediction_input = {}

    if page == "prediction" and request.method == "POST":
        prediction_input = request.form.to_dict()

        try:
            air = float(request.form["air_temperature"])
            process = float(request.form["process_temperature"])
            speed = float(request.form["rotational_speed"])
            torque = float(request.form["torque"])
            wear = float(request.form["tool_wear"])
            machine_type = request.form["machine_type"]

            if machine_type not in ["L", "M", "H"]:
                raise ValueError("Please select a valid machine type.")

            if not (250 <= air <= 350):
                raise ValueError("Air temperature must be between 250 and 350 K.")

            if not (250 <= process <= 400):
                raise ValueError("Process temperature must be between 250 and 400 K.")

            if not (100 <= speed <= 5000):
                raise ValueError("Rotational speed must be between 100 and 5000 rpm.")

            if not (0 <= torque <= 100):
                raise ValueError("Torque must be between 0 and 100 Nm.")

            if not (0 <= wear <= 300):
                raise ValueError("Tool wear must be between 0 and 300 minutes.")

            features = [
                air,
                process,
                speed,
                torque,
                wear,
                1 if machine_type == "L" else 0,
                1 if machine_type == "M" else 0,
                1 if machine_type == "H" else 0,
                process - air,
                torque * speed / 1000
            ]

            verify_ai4i_model(MODEL_PATH)

            with open(MODEL_PATH, "rb") as model_file:
                model = pickle.load(model_file)

            votes = 0

            for tree in model["trees"]:
                node = tree

                while node["feature"] is not None:
                    if features[node["feature"]] <= node["threshold"]:
                        node = node["left"]
                    else:
                        node = node["right"]

                votes += int(node["prediction"])

            failure_score = votes / len(model["trees"])
            decision_threshold = round(float(model["threshold"]), 2)
            predicted_class = int(failure_score >= decision_threshold)

            prediction_result = {
                "prediction": predicted_class,
                "score": round(failure_score * 100, 2)
            }

        except FileNotFoundError:
            prediction_error = (
                "The trained model file was not found. Check that "
                "models/ai4i_random_forest.pkl exists."
            )
        except (ValueError, KeyError, ZeroDivisionError) as error:
            prediction_error = str(error) or "Unable to calculate a prediction."
        except Exception as error:
            prediction_error = (
                "The model could not generate a prediction. "
                "Check the saved model file. Details: " + str(error)
            )

    maintenance_alerts = []
    maintenance_tasks = []
    m_severity = request.args.get("m_severity", "all")
    if m_severity not in ("all", "HIGH", "MEDIUM", "LOW"):
        m_severity = "all"
    m_status = request.args.get("m_status", "all")
    if m_status not in ("all", "acknowledged", "unacknowledged"):
        m_status = "all"
    m_limit = request.args.get("m_limit", "50")
    if m_limit not in ("20", "50", "100", "all"):
        m_limit = "50"
    try:
        m_page = max(1, int(request.args.get("m_page", "1")))
    except (ValueError, TypeError):
        m_page = 1
    m_total, m_start, m_end, m_pages = 0, 0, 0, 1
    maintenance_notice = request.args.get("notice", "")[:150]
    maintenance_error = request.args.get("error", "")[:150]
    csrf_token = maintenance_csrf_token() if page == "maintenance" else None

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()
        available_assets = [row[0] for row in cursor.execute("""
            SELECT DISTINCT asset_id FROM sensor_readings
            WHERE asset_id IS NOT NULL AND asset_id != ''
            UNION
            SELECT DISTINCT asset_id FROM alerts
            WHERE asset_id IS NOT NULL AND asset_id != ''
            ORDER BY asset_id
        """).fetchall()]
        selected_asset = request.args.get("asset", "all")
        if selected_asset != "all" and selected_asset not in available_assets:
            selected_asset = "all"
        asset_condition = " AND asset_id = ?" if selected_asset != "all" else ""
        asset_parameters = [selected_asset] if selected_asset != "all" else []
        if page == "maintenance":
            create_maintenance_tables(conn)
            where = []
            params = []
            if selected_asset != "all":
                where.append("a.asset_id = ?")
                params.append(selected_asset)
            if m_severity != "all":
                where.append("a.severity = ?")
                params.append(m_severity)
            if m_status == "acknowledged":
                where.append("ack.alert_id IS NOT NULL")
            elif m_status == "unacknowledged":
                where.append("ack.alert_id IS NULL")
            where_sql = " WHERE " + " AND ".join(where) if where else ""
            from_sql = " FROM alerts a LEFT JOIN alert_acknowledgements ack ON ack.alert_id = a.id"
            m_total = cursor.execute(
                "SELECT COUNT(*)" + from_sql + where_sql, params
            ).fetchone()[0]
            m_size = 100 if m_limit == "all" else int(m_limit)
            m_pages = max(1, (m_total + m_size - 1) // m_size)
            m_page = min(m_page, m_pages)
            offset = (m_page - 1) * m_size
            maintenance_alerts = cursor.execute(
                "SELECT a.id, a.timestamp, a.sensor, a.severity, a.asset_id, a.source, "
                "ack.operator, ack.acknowledged_at" + from_sql + where_sql +
                " ORDER BY a.id DESC LIMIT ? OFFSET ?",
                params + [m_size, offset]
            ).fetchall()
            m_start = offset + 1 if m_total else 0
            m_end = offset + len(maintenance_alerts)
            maintenance_tasks = cursor.execute("""
                SELECT id, created_at, asset_id, priority, assigned_to, scheduled_for,
                       description, status, completed_at, completion_notes
                FROM maintenance_tasks ORDER BY id DESC LIMIT 100
            """).fetchall()

        def parse_units(raw):
            try:
                return {k: v for k, v in json.loads(raw or "{}").items() if isinstance(v, str)}
            except (ValueError, TypeError, AttributeError):
                return {}

        cursor.execute("SELECT asset_id, source, run_id, units_json, synthetic_fields_json FROM sensor_readings WHERE 1=1" + asset_condition + " ORDER BY id DESC LIMIT 1", asset_parameters)
        context = cursor.fetchone()
        latest_asset, latest_source, latest_sensor_run, raw_units, raw_synthetic = context or (None, None, None, None, None)
        display_units = {sensor: parse_units(raw_units).get(sensor) or UNITS[sensor] for sensor in SENSORS}
        try:
            latest_synthetic = json.loads(raw_synthetic or "[]")
        except (ValueError, TypeError):
            latest_synthetic = []
        # Latest 30 readings for graphs, restricted to a single source and run.
        cursor.execute("""
            SELECT timestamp, temperature, vibration,
                   humidity, pressure, current
            FROM sensor_readings
            WHERE asset_id IS ? AND source IS ? AND run_id IS ? AND units_json IS ?
            ORDER BY id DESC
            LIMIT 30
        """, (latest_asset, latest_source, latest_sensor_run, raw_units))

        graph_readings = cursor.fetchall()

        # Reading history uses a bounded page size, including All Entries.
        history_limit = request.args.get("history_limit", "100")
        if history_limit not in ["20", "50", "100", "all"]:
            history_limit = "100"

        history_page_size = 100 if history_limit == "all" else int(history_limit)
        try:
            readings_page = max(1, int(request.args.get("history_page", "1")))
        except ValueError:
            readings_page = 1

        cursor.execute("SELECT COUNT(*) FROM sensor_readings WHERE 1=1" + asset_condition, asset_parameters)
        readings_total = cursor.fetchone()[0]
        readings_total_pages = max(1, (readings_total + history_page_size - 1) // history_page_size)
        readings_page = min(readings_page, readings_total_pages)
        readings_offset = (readings_page - 1) * history_page_size

        cursor.execute("""
            SELECT timestamp, temperature, vibration,
                   humidity, pressure, current, asset_id, source, units_json, synthetic_fields_json
            FROM sensor_readings
            WHERE 1=1 {asset_filter}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """.replace("{asset_filter}", asset_condition), (*asset_parameters, history_page_size, readings_offset))

        readings = []
        for row in cursor.fetchall():
            row_units = parse_units(row[8])
            try:
                synthetic = json.loads(row[9] or "[]")
            except (ValueError, TypeError):
                synthetic = []
            readings.append([row[0], row[6] or "Unknown", row[7] or "Unknown"] + [f"{row[i]} {(row_units.get(sensor) or UNITS[sensor])}" + (" (synthetic)" if sensor in synthetic else "") for i, sensor in enumerate(SENSORS, 1)])
        readings_start = readings_offset + 1 if readings_total else 0
        readings_end = min(readings_offset + len(readings), readings_total)

        latest = {}

        if graph_readings:

            latest = {
                "temperature": round(graph_readings[0][1], 2),
                "vibration": round(graph_readings[0][2], 2),
                "humidity": round(graph_readings[0][3], 2),
                "pressure": round(graph_readings[0][4], 2),
                "current": round(graph_readings[0][5], 2)
            }

        # Current status uses the latest reading, not historical alert totals.
        # Thresholds below are demonstration limits for the simulated source.
        machine_status = "NO RECENT DATA"
        machine_status_detail = "No recent sensor reading is available."
        if graph_readings:
            try:
                raw_time = graph_readings[0][0]
                reading_time = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
                if reading_time.tzinfo is None:
                    reading_time = reading_time.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - reading_time.astimezone(timezone.utc)
                if timedelta(0) <= age <= timedelta(minutes=2):
                    if latest_source != "simulated_sensor":
                        machine_status_detail = (
                            "Recent readings received. Current status thresholds "
                            "are defined only for the simulated sensor source."
                        )
                    else:
                        abnormal = []
                        if latest["temperature"] > 50:
                            abnormal.append("elevated temperature")
                        if latest["vibration"] > 8:
                            abnormal.append("elevated vibration")
                        prior = graph_readings[1:11]
                        if len(prior) >= 5:
                            humidity_mean = sum(float(r[3]) for r in prior) / len(prior)
                            if latest["humidity"] > humidity_mean + 15:
                                abnormal.append("humidity deviation")
                        if abnormal:
                            machine_status = "WARNING"
                            machine_status_detail = (
                                "Latest readings indicate " + ", ".join(abnormal) +
                                ". Inspect the equipment and review maintenance alerts."
                            )
                        else:
                            machine_status = "NORMAL"
                            machine_status_detail = (
                                "No anomaly detected by the dashboard's current-reading "
                                "checks. This is not a guarantee of equipment health."
                            )
                else:
                    machine_status_detail = "Latest reading is older than two minutes or has an invalid future timestamp."
            except (ValueError, TypeError, OverflowError):
                machine_status_detail = "Latest reading timestamp could not be validated."

        chronological = list(reversed(graph_readings))

        timestamps = [
            row[0] for row in chronological
        ]

        sensor_data = {}

        for index, sensor in enumerate(SENSORS, start=1):

            sensor_data[sensor] = [
                row[index] for row in chronological
            ]

        # Latest alert for each sensor
        cursor.execute("""
            SELECT sensor, severity, timestamp
            FROM alerts
            WHERE asset_id IS ? AND source IS ? AND run_id IS ?
            ORDER BY id DESC
        """, (latest_asset, latest_source, latest_sensor_run))

        last_alerts = {}

        for sensor, severity, timestamp in cursor.fetchall():

            if sensor not in last_alerts:
                last_alerts[sensor] = (severity, timestamp)

        # Alert summary counts
        cursor.execute("""
            SELECT severity, COUNT(*)
            FROM alerts
            WHERE 1=1 {asset_filter}
            GROUP BY severity
        """.replace("{asset_filter}", asset_condition), asset_parameters)

        severity_results = cursor.fetchall()

        alert_counts = {
            "TOTAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }

        for severity, count in severity_results:

            alert_counts["TOTAL"] += count

            if severity in alert_counts:
                alert_counts[severity] = count

        # Apply alert filters
        selected_sensor = request.args.get("sensor", "all")
        selected_severity = request.args.get("severity", "all")

        if selected_sensor not in ["all"] + SENSORS:
            selected_sensor = "all"

        if selected_severity not in ["all", "HIGH", "MEDIUM", "LOW"]:
            selected_severity = "all"

        alert_query = """
            SELECT timestamp, sensor, reading, z_score,
                   severity, recommendation, unit, asset_id, source
            FROM alerts
            WHERE 1 = 1
        """

        parameters = list(asset_parameters)
        alert_query += asset_condition

        if selected_sensor != "all":
            alert_query += " AND sensor = ?"
            parameters.append(selected_sensor)

        if selected_severity != "all":
            alert_query += " AND severity = ?"
            parameters.append(selected_severity)

        alert_limit = request.args.get("alert_limit", "100")
        if alert_limit not in ["20", "50", "100", "all"]:
            alert_limit = "100"

        alert_page_size = 100 if alert_limit == "all" else int(alert_limit)
        try:
            alerts_page = max(1, int(request.args.get("alert_page", "1")))
        except ValueError:
            alerts_page = 1

        count_query = "SELECT COUNT(*) FROM alerts WHERE 1 = 1"
        count_query += asset_condition
        count_parameters = list(asset_parameters)

        if selected_sensor != "all":
            count_query += " AND sensor = ?"
            count_parameters.append(selected_sensor)

        if selected_severity != "all":
            count_query += " AND severity = ?"
            count_parameters.append(selected_severity)

        cursor.execute(count_query, count_parameters)
        alerts_total = cursor.fetchone()[0]
        alerts_total_pages = max(1, (alerts_total + alert_page_size - 1) // alert_page_size)
        alerts_page = min(alerts_page, alerts_total_pages)
        alerts_offset = (alerts_page - 1) * alert_page_size

        alert_query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        parameters.extend([alert_page_size, alerts_offset])

        cursor.execute(alert_query, parameters)
        alerts = cursor.fetchall()
        alerts_start = alerts_offset + 1 if alerts_total else 0
        alerts_end = min(alerts_offset + len(alerts), alerts_total)


        # AI4I replay prediction summary and paginated history.
        prediction_limit = request.args.get("prediction_limit", "100")
        if prediction_limit not in ["20", "50", "100", "all"]:
            prediction_limit = "100"

        predictions_page_size = 100 if prediction_limit == "all" else int(prediction_limit)
        try:
            predictions_page = max(1, int(request.args.get("prediction_page", "1")))
        except ValueError:
            predictions_page = 1

        prediction_metrics = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0
        }
        latest_prediction_metrics = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
            "start_timestamp": None,
            "end_timestamp": None
        }
        latest_run_id = None
        legacy_prediction_count = 0
        prediction_history = []
        predictions_total = 0
        predictions_total_pages = 1
        predictions_start = 0
        predictions_end = 0

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'predictions'
        """)
        predictions_table_exists = cursor.fetchone() is not None

        if predictions_table_exists:
            cursor.execute("""
                SELECT
                    COUNT(*),
                    COALESCE(SUM(correct), 0),
                    COALESCE(SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN predicted_failure = 1 AND actual_failure = 1 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN predicted_failure = 1 AND actual_failure = 0 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN predicted_failure = 0 AND actual_failure = 1 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN predicted_failure = 0 AND actual_failure = 0 THEN 1 ELSE 0 END), 0)
                FROM predictions
            """)

            (
                prediction_total_count,
                prediction_correct_count,
                prediction_incorrect_count,
                prediction_true_positives,
                prediction_false_positives,
                prediction_false_negatives,
                prediction_true_negatives
            ) = cursor.fetchone()

            prediction_accuracy = (
                round(prediction_correct_count / prediction_total_count * 100, 2)
                if prediction_total_count else 0.0
            )

            prediction_metrics = {
                "total": prediction_total_count,
                "correct": prediction_correct_count,
                "incorrect": prediction_incorrect_count,
                "accuracy": prediction_accuracy,
                "true_positives": prediction_true_positives,
                "false_positives": prediction_false_positives,
                "false_negatives": prediction_false_negatives,
                "true_negatives": prediction_true_negatives
            }

            cursor.execute("SELECT COUNT(*) FROM predictions WHERE run_id IS NULL OR run_id = ''")
            legacy_prediction_count = cursor.fetchone()[0]
            cursor.execute("SELECT run_id FROM predictions WHERE source = 'ai4i_replay' AND run_id IS NOT NULL AND run_id != '' ORDER BY id DESC LIMIT 1")
            latest_run = cursor.fetchone()
            latest_run_id = latest_run[0] if latest_run else None

            if latest_run_id is not None:
                cursor.execute("""
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(correct), 0),
                        COALESCE(SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN predicted_failure = 1 AND actual_failure = 1 THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN predicted_failure = 1 AND actual_failure = 0 THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN predicted_failure = 0 AND actual_failure = 1 THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN predicted_failure = 0 AND actual_failure = 0 THEN 1 ELSE 0 END), 0),
                        MIN(timestamp),
                        MAX(timestamp)
                    FROM predictions
                    WHERE run_id = ? AND source = 'ai4i_replay'
                """, (latest_run_id,))

                (
                    latest_total,
                    latest_correct,
                    latest_incorrect,
                    latest_true_positives,
                    latest_false_positives,
                    latest_false_negatives,
                    latest_true_negatives,
                    latest_start_timestamp,
                    latest_end_timestamp
                ) = cursor.fetchone()

                latest_accuracy = (
                    round(latest_correct / latest_total * 100, 2)
                    if latest_total else 0.0
                )

                latest_prediction_metrics = {
                    "total": latest_total,
                    "correct": latest_correct,
                    "incorrect": latest_incorrect,
                    "accuracy": latest_accuracy,
                    "true_positives": latest_true_positives,
                    "false_positives": latest_false_positives,
                    "false_negatives": latest_false_negatives,
                    "true_negatives": latest_true_negatives,
                    "start_timestamp": latest_start_timestamp,
                    "end_timestamp": latest_end_timestamp
                }

            predictions_total = prediction_total_count
            predictions_total_pages = max(
                1,
                (predictions_total + predictions_page_size - 1) // predictions_page_size
            )
            predictions_page = min(predictions_page, predictions_total_pages)
            predictions_offset = (predictions_page - 1) * predictions_page_size

            cursor.execute("""
                SELECT
                    timestamp,
                    udi,
                    product_id,
                    machine_type,
                    failure_score,
                    threshold,
                    predicted_failure,
                    actual_failure,
                    correct, run_id
                FROM predictions
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (predictions_page_size, predictions_offset))

            prediction_history = cursor.fetchall()
            predictions_start = predictions_offset + 1 if predictions_total else 0
            predictions_end = min(
                predictions_offset + len(prediction_history),
                predictions_total
            )


    # Notification read state is stored in the browser session; alerts are never deleted.
    notification_items = []
    notification_unread = 0
    notification_page = 1
    notification_pages = 1
    notification_total = 0
    notification_start = 0
    notification_end = 0
    n_severity = request.args.get("n_severity", "all").upper()
    if n_severity not in ("all", "HIGH", "MEDIUM", "LOW"):
        n_severity = "all"
    n_sensor = request.args.get("n_sensor", "all").lower()
    if n_sensor not in ("all", *SENSORS):
        n_sensor = "all"

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as notification_conn:
            latest_notification_id = notification_conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM alerts"
            ).fetchone()[0]
            last_seen = session.get("notification_last_seen_id")
            if last_seen is None:
                # Existing historical alerts start as read for this browser session.
                last_seen = latest_notification_id
                session["notification_last_seen_id"] = last_seen
            if page == "notifications":
                session["notification_last_seen_id"] = latest_notification_id
            else:
                notification_unread = notification_conn.execute(
                    "SELECT COUNT(*) FROM alerts WHERE id > ?" + asset_condition,
                    (last_seen, *asset_parameters)
                ).fetchone()[0]
            if page == "notifications":
                conditions = []
                parameters = []
                if selected_asset != "all":
                    conditions.append("asset_id = ?")
                    parameters.append(selected_asset)
                if n_severity != "all":
                    conditions.append("severity = ?")
                    parameters.append(n_severity)
                if n_sensor != "all":
                    conditions.append("sensor = ?")
                    parameters.append(n_sensor)
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                notification_total = notification_conn.execute(
                    "SELECT COUNT(*) FROM alerts" + where_clause, parameters
                ).fetchone()[0]
                notification_pages = max(1, (notification_total + 49) // 50)
                try:
                    notification_page = max(1, int(request.args.get("n_page", "1")))
                except ValueError:
                    notification_page = 1
                notification_page = min(notification_page, notification_pages)
                notification_items = notification_conn.execute(
                    """SELECT id, timestamp, sensor, reading, severity, recommendation,
                              asset_id, source, unit
                       FROM alerts""" + where_clause + " ORDER BY id DESC LIMIT 50 OFFSET ?",
                    (*parameters, (notification_page - 1) * 50)
                ).fetchall()
                notification_start = (notification_page - 1) * 50 + 1 if notification_total else 0
                notification_end = min(notification_start + len(notification_items) - 1, notification_total) if notification_total else 0

    return render_template_string(
        HTML,
        notification_items=notification_items,
        notification_unread=notification_unread,
        notification_page=notification_page,
        notification_pages=notification_pages,
        notification_total=notification_total,
        notification_start=notification_start,
        notification_end=notification_end,
        n_severity=n_severity,
        n_sensor=n_sensor,
        page=page,
        pages=PAGES,
        available_assets=available_assets,
        selected_asset=selected_asset,
        maintenance_alerts=maintenance_alerts,
        maintenance_tasks=maintenance_tasks,
        m_severity=m_severity,
        m_status=m_status,
        m_limit=m_limit,
        m_page=m_page,
        m_pages=m_pages,
        m_total=m_total,
        m_start=m_start,
        m_end=m_end,
        maintenance_notice=maintenance_notice,
        maintenance_error=maintenance_error,
        csrf_token=csrf_token,
        page_title=page_title,
        page_description=page_description,
        sensors=SENSORS,
        sensor_labels=SENSOR_LABELS,
        units=display_units,
        latest_run_id=latest_run_id,
        legacy_prediction_count=legacy_prediction_count,
        latest_source=latest_source,
        latest_asset=latest_asset,
        latest_synthetic=latest_synthetic,
        latest=latest,
        last_alerts=last_alerts,
        machine_status=machine_status,
        machine_status_detail=machine_status_detail,
        alert_counts=alert_counts,
        readings=readings,
        alerts=alerts,
        history_limit=history_limit,
        history_page_size=history_page_size,
        readings_page=readings_page,
        readings_total=readings_total,
        readings_total_pages=readings_total_pages,
        readings_start=readings_start,
        readings_end=readings_end,
        alert_limit=alert_limit,
        alert_page_size=alert_page_size,
        alerts_page=alerts_page,
        alerts_total=alerts_total,
        alerts_total_pages=alerts_total_pages,
        alerts_start=alerts_start,
        alerts_end=alerts_end,
        timestamps=timestamps,
        sensor_data=sensor_data,
        selected_sensor=selected_sensor,
        selected_severity=selected_severity,
        prediction_result=prediction_result,
        prediction_error=prediction_error,
        prediction_input=prediction_input,
        prediction_metrics=prediction_metrics,
        latest_prediction_metrics=latest_prediction_metrics,
        prediction_history=prediction_history,
        prediction_limit=prediction_limit,
        predictions_page_size=predictions_page_size,
        predictions_page=predictions_page,
        predictions_total=predictions_total,
        predictions_total_pages=predictions_total_pages,
        predictions_start=predictions_start,
        predictions_end=predictions_end
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0" if os.getenv("DOCKER_ENV") == "1" else "127.0.0.1", port=5000, debug=False, use_reloader=False)
