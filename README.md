# IoT-Based Predictive Maintenance System

An end-to-end industrial equipment monitoring prototype that simulates five sensors, streams readings through MQTT, detects abnormal behaviour, records maintenance alerts, and provides a web dashboard with machine-failure prediction.

## Features

- **Live sensor monitoring:** temperature, vibration, humidity, pressure and electrical current.
- **MQTT streaming:** authenticated, TLS-enabled communication between the simulated publisher, Mosquitto broker and consumer.
- **Hybrid anomaly detection:** temperature spikes, abnormal temperature increases, irregular vibration, and sustained humidity drift; additional simulated pressure/current faults support monitoring tests.
- **Maintenance alerts:** severity levels, sensor-specific recommendations, alert history and maintenance management.
- **Web dashboard:** Overview, Live Sensors, Maintenance Alerts, Reading History, Machine Failure Prediction, Replay Prediction Results and Maintenance Management.
- **Failure classification:** a custom NumPy-based Random Forest trained on the AI4I 2020 dataset.
- **Reproducibility:** evaluation scripts, automated tests, dataset attribution and saved evaluation results.

## System architecture

```text
Simulated sensors (5)
        |
        v
MQTT Publisher --> Mosquitto Broker --> MQTT Consumer
                                            |
                                  Hybrid anomaly detection
                                            |
                                            v
                                       SQLite database
                                            |
                                            v
                                  Flask monitoring dashboard
                                            |
                                   Alerts and maintenance

AI4I dataset --> Feature processing --> Random Forest --> Failure classification
```

The AI4I failure-classification workflow is separate from the live five-sensor anomaly-detection workflow.

## Quick start: run the project on Windows

**Prerequisites:** Python 3.12, Git, Mosquitto MQTT broker and Windows Command Prompt (CMD). The project was tested on Windows 10 ARM64 with Python 3.12.10. Use the **same cloned project folder** for every CMD window so all processes share the same local SQLite database.

### 1. Clone and install

Copy the repository's HTTPS clone URL from GitHub:

```cmd
git clone <YOUR_REPOSITORY_HTTPS_URL>
cd <CLONED_PROJECT_FOLDER>
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Configure the MQTT broker (once per computer)

The Python clients expect a **running Mosquitto broker at `localhost:8883` with TLS**, two broker accounts and appropriate topic permissions:

| Role | MQTT username | Password variable |
|---|---|---|
| Consumer | `maintenance_consumer` | `MQTT_CONSUMER_PASSWORD` |
| Publisher / AI4I replay | `maintenance_publisher` | `MQTT_PUBLISHER_PASSWORD` |

Create the two accounts in the Mosquitto password file, choose their passwords, configure the broker's TLS listener and ACLs, and place the trusted local broker certificate at `%USERPROFILE%\mqtt_tls\server.crt`. The certificate must be valid for `localhost`. Start the broker using **your own configured Mosquitto configuration file**, or confirm that its Windows service is already running:

```cmd
mosquitto -c <PATH_TO_YOUR_MOSQUITTO_CONFIG> -v
```

The broker configuration, TLS certificates and passwords are **local setup items** and are not included in GitHub. Simply running an unsecured default Mosquitto broker will not satisfy the clients' TLS and authentication settings. Do not start a second broker if the configured broker service is already running.

### 3. Start the MQTT consumer — CMD window 1

Open a new CMD window in the cloned project folder:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_CONSUMER_PASSWORD=Enter MQTT consumer password: 
python -m messaging.consumer
```

Enter the password assigned to `maintenance_consumer` in Mosquitto. **Keep this window running.** The consumer subscribes to sensor and replay topics, processes readings and stores alerts in SQLite.

### 4. Start the simulated sensor publisher — CMD window 2

Open another CMD window in the **same project folder**:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password: 
python -m messaging.publisher
```

Enter the password assigned to `maintenance_publisher` in Mosquitto. **Keep this window running.** It publishes sensor readings and simulated faults.

**To see new live readings and alerts, both the consumer and publisher must be running, alongside the MQTT broker.** Opening the dashboard alone only shows previously stored data (if any).

### 5. Start the dashboard and sign in — CMD window 3

Open a third CMD window in the **same project folder**:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set "DASHBOARD_USERNAME=admin"
set /p DASHBOARD_PASSWORD=Enter dashboard login password: 
python -m dashboard.app
```

Choose a dashboard password at the prompt. The dashboard login credentials are **separate from the MQTT passwords**. Keep this CMD window running, then open:

**http://127.0.0.1:5000**

Sign in with username **`admin`** and the dashboard password you entered. Visit **Overview**, **Live Sensors**, **Maintenance Alerts** and **Reading History** to observe incoming data.

> **Password note:** `set /p` displays the password while typing. Use these commands only in a trusted local environment and avoid sharing screenshots of credentials. Environment variables set in one CMD window do not automatically carry over to other windows.

### 6. Optional: populate replay prediction records

With Mosquitto and the consumer still running, open another CMD window:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password: 
python -m messaging.ai4i_replay_publisher
```

The replay publishes AI4I machine records for processing and storage. Refresh **Replay Prediction Results** in the dashboard to view saved replay predictions. The **Machine Failure Prediction** page also supports entering operating parameters manually.

### Quick troubleshooting

| Problem | Check |
|---|---|
| No new live readings | Mosquitto, consumer **and** publisher must all be running. |
| MQTT authentication error | Enter the password matching the correct Mosquitto account in that CMD window. |
| MQTT TLS/certificate error | Verify port `8883`, broker TLS configuration and `%USERPROFILE%\mqtt_tls\server.crt`. |
| Dashboard login fails | Set both `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` **before** starting `python -m dashboard.app`. |
| Dashboard shows no history | A fresh clone starts without the original developer's local SQLite history; generate readings first. |
| Replay results do not appear | Run the AI4I replay, keep the consumer active and ensure all processes use the same clone. |

## Sensor simulation and anomaly detection

| Sensor | Typical simulated range | Unit |
|---|---|---|
| Temperature | 35–45 | °C |
| Vibration | 1–5 | mm/s |
| Humidity | 30–70 | % |
| Pressure | 2–6 | bar |
| Current | 5–20 | A |

The publisher simulates temperature spikes, rising temperatures, vibration spikes, humidity drift, pressure drops and current surges. The live hybrid detector combines direct thresholds with recent-history comparisons and sustained-trend checks. Alert processing assigns severity levels and sensor-specific maintenance recommendations. The system also retains rolling Z-score detection for applicable evaluation/replay workflows.

MQTT topics:

- `factory/sensors` — simulated sensor readings.
- `factory/ai4i/replay` — AI4I replay records.

Events include traceability metadata such as asset ID, source, timestamps, event ID, run ID, units and schema version. SQLite stores readings, alerts, predictions and maintenance-related records.

## Dashboard modules

| Module | Purpose |
|---|---|
| Overview | Latest sensor values, equipment status and monitoring summary |
| Live Sensors | Near-real-time charts for all five sensors |
| Maintenance Alerts | Detected anomalies, severity and recommendations |
| Reading History | Stored sensor measurements and history controls |
| Machine Failure Prediction | Manual AI4I operating inputs and failure classification |
| Replay Prediction Results | Stored AI4I replay predictions |
| Maintenance Management | Alert acknowledgement, maintenance scheduling and status tracking |

## Model and evaluation results

### AI4I 2020 — machine-failure classification

A custom Python/NumPy Random Forest (25 trees, maximum depth 8) was trained and evaluated using the AI4I 2020 Predictive Maintenance dataset (10,000 records: 6,999 training, 1,500 validation and 1,501 test).

| Held-out test metric | Result |
|---|---:|
| Accuracy | **97.80%** |
| Precision | **70.45%** |
| Recall | **60.78%** |
| F1-score | **65.26%** |
| True positives / false positives | 31 / 13 |
| False negatives / true negatives | 20 / 1,437 |

The prediction page classifies the entered AI4I operating conditions as normal or failure risk. Its displayed model score reflects the Random Forest's voting score, not a calibrated probability of failure.

### Simulated sensor anomaly detection

The hybrid detector was evaluated on labelled historical simulated-sensor runs and compared with a rolling Z-score baseline.

| Fixed test run (418 readings) | Z-score baseline | Hybrid detector |
|---|---:|---:|
| Precision | 45.98% | **87.05%** |
| Recall | 68.18% | **68.75%** |
| F1-score | 54.92% | **76.83%** |
| False positives | 141 | **18** |

The updated detector also passed targeted tests for gradual temperature increases and sustained humidity drift. Fixed run IDs make the comparison reproducible; they do not independently establish a previously untouched holdout set.

Evaluation files:

```cmd
python -m detection.evaluate_hybrid
python detection\evaluate_skab_final.py
```

Saved reports include `results/hybrid_evaluation.json` and `results/skab_final_evaluation.json`. SKAB and NAB are used for additional anomaly-detection experiments; AI4I is used for failure classification.

## Testing

Run the automated test suite:

```cmd
run_tests.bat
```

Or:

```cmd
python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector -q
```

A clean-clone check on 22 November 2026 reported **28 passing automated tests**, successful authenticated MQTT sensor ingestion, dashboard sign-in and an AI4I replay of 100 records.

## Technologies

Python 3.12, Flask, Paho-MQTT, Mosquitto, SQLite, NumPy, HTML, CSS, JavaScript and Git/GitHub. The final AI4I Random Forest implementation does not require scikit-learn at runtime.

## Security and datasets

The project uses MQTT username/password authentication, local TLS communication on port `8883`, broker ACLs, dashboard login, CSRF protection for maintenance actions and SHA-256 integrity verification for the saved AI4I model. **Never commit passwords, broker private keys or password files.** The supplied configuration is intended for a local demonstration environment.

Dataset provenance and redistribution information are recorded in `DATASET_ATTRIBUTION.md` (including AI4I, SKAB and NAB). The local SQLite database, broker credentials and TLS private material are not bundled with the repository.

## Summary

This project demonstrates a working IoT predictive-maintenance workflow: sensor simulation, authenticated streaming, anomaly detection, alert management, live visualisation, and machine-failure classification, supported by reproducible tests and evaluation results.
