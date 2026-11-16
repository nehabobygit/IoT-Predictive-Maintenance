
import sqlite3
import pickle
from pathlib import Path
from flask import Flask, render_template_string, request

app = Flask(__name__)

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
    ("prediction", "Machine Failure Prediction", "brain-circuit")
]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Industrial Predictive Maintenance</title>

    <meta name="viewport" content="width=device-width, initial-scale=1">
    {% if page != "prediction" %}<meta http-equiv="refresh" content="5">{% endif %}

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
                    href="/?page={{ key }}"
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

            <p class="section-description">
                Latest readings received from all five sensors.
            </p>

            {% if latest %}

                <div class="sensor-grid">

                    {% for sensor in sensors %}

                        <div class="card sensor-card">

                            <div class="card-label">
                                {{ sensor_labels[sensor] }}
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
                            <th>Reading</th>
                            <th>Severity</th>
                            <th>Recommended Action</th>
                        </tr>

                        {% for alert in alerts[:6] %}
                            <tr>
                                <td>{{ alert[0] }}</td>
                                <td>{{ sensor_labels.get(alert[1], alert[1]) }}</td>
                                <td>{{ alert[2] }}</td>
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


        {% elif page == "sensors" %}

            <div class="info-banner">
                <strong>Live sensor monitoring:</strong>
                View individual sensor readings and their recent trends.
                Graphs show the latest 30 readings.
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

                <a href="/?page=alerts" class="reset-link">
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
                            <th>Reading</th>
                            <th>Z-score</th>
                            <th>Severity</th>
                            <th>Recommended Maintenance Action</th>
                        </tr>

                        {% for alert in alerts %}

                            <tr>
                                <td>{{ alert[0] }}</td>
                                <td>{{ sensor_labels.get(alert[1], alert[1]) }}</td>
                                <td>{{ alert[2] }}</td>
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
                            <a href="{{ url_for('dashboard', page='alerts', sensor=selected_sensor, severity=selected_severity, alert_limit=alert_limit, alert_page=alerts_page-1) }}">Previous</a>
                        {% endif %}
                        <span>{{ alerts_page }} / {{ alerts_total_pages }}</span>
                        {% if alerts_page < alerts_total_pages %}
                            <a href="{{ url_for('dashboard', page='alerts', sensor=selected_sensor, severity=selected_severity, alert_limit=alert_limit, alert_page=alerts_page+1) }}">Next</a>
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


        {% elif page == "history" %}

            <div class="info-banner">
                <strong>Sensor reading history:</strong>
                Review the latest readings stored by the monitoring system.
            </div>

            <h2>Latest Sensor Readings</h2>

            <form method="GET" action="/" class="filter-bar">
                <input type="hidden" name="page" value="history">
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
                {% if history_limit == "all" %}All Entries is displayed in pages of 100 to keep the dashboard responsive.{% else %}Displaying up to {{ readings_page_size }} records per page.{% endif %}
            </p>

            {% if readings %}

                <div class="table-container">
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>Temperature (°C)</th>
                            <th>Vibration (mm/s)</th>
                            <th>Humidity (%)</th>
                            <th>Pressure (bar)</th>
                            <th>Current (A)</th>
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
                            <a href="{{ url_for('dashboard', page='history', history_limit=history_limit, history_page=readings_page-1) }}">Previous</a>
                        {% endif %}
                        <span>{{ readings_page }} / {{ readings_total_pages }}</span>
                        {% if readings_page < readings_total_pages %}
                            <a href="{{ url_for('dashboard', page='history', history_limit=history_limit, history_page=readings_page+1) }}">Next</a>
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
            predicted_class = int(failure_score >= model["threshold"])

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

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        # Latest 30 readings for graphs
        cursor.execute("""
            SELECT timestamp, temperature, vibration,
                   humidity, pressure, current
            FROM sensor_readings
            ORDER BY id DESC
            LIMIT 30
        """)

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

        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        readings_total = cursor.fetchone()[0]
        readings_total_pages = max(1, (readings_total + history_page_size - 1) // history_page_size)
        readings_page = min(readings_page, readings_total_pages)
        readings_offset = (readings_page - 1) * history_page_size

        cursor.execute("""
            SELECT timestamp, temperature, vibration,
                   humidity, pressure, current
            FROM sensor_readings
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (history_page_size, readings_offset))

        readings = cursor.fetchall()
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
            ORDER BY id DESC
        """)

        last_alerts = {}

        for sensor, severity, timestamp in cursor.fetchall():

            if sensor not in last_alerts:
                last_alerts[sensor] = (severity, timestamp)

        # Alert summary counts
        cursor.execute("""
            SELECT severity, COUNT(*)
            FROM alerts
            GROUP BY severity
        """)

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
                   severity, recommendation
            FROM alerts
            WHERE 1 = 1
        """

        parameters = []

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
        count_parameters = []

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



    return render_template_string(
        HTML,
        page=page,
        pages=PAGES,
        page_title=page_title,
        page_description=page_description,
        sensors=SENSORS,
        sensor_labels=SENSOR_LABELS,
        units=UNITS,
        latest=latest,
        last_alerts=last_alerts,
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
        prediction_input=prediction_input
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
