# IoT Predictive Maintenance Project Audit

Verified on 26 November 2026 using Python 3.12.10, the installed Windows Mosquitto broker software, SQLite and Chrome.

## Initial assessment and implementation

| Area | Initial state | Implemented and verified |
|---|---|---|
| Sensors and machines | Five sensor fields and six injected fault patterns. The message contract and publisher accepted one simulator asset. Normal readings varied independently. | Three machines with correlated load cycles, different operating ranges, staggered faults, bidirectional humidity drift, combined faults and progressive degradation. |
| MQTT and storage | Authenticated MQTT over TLS, two topics, SQLite, UUID deduplication and an existing alert lifecycle. | Kept existing message and database contracts, enabled WAL, consolidated history queries and added transactional anomaly and forecast records. |
| Anomalies and alerts | Fixed bounds and rolling rules, with detection saved only through the alert cooldown. Dashboard status used a second set of threshold checks. | Per-reading anomaly events and reason text, sensor-specific rules, Low/Medium/High severity, cooldown-limited alerts and a dashboard status based on the ingested results. |
| Prediction | AI4I manual and replay predictions used a 25-tree classifier for concurrent failure. The five live sensor fields did not supply AI4I inputs or feed a forecasting model. | Replaced the default AI4I classifier and added a separately trained six-sample forecast driven by recent telemetry. Both manual and replay AI4I predictions use the same feature and scoring code. |
| Dashboard | Existing Flask pages, asset filters, maintenance controls and a five-second refresh. Model metrics were literal values and chart loading depended on a CDN. | Existing theme and navigation with fleet status, current sensor values and timestamps, live outlook, alert explanations and acknowledgement, local charts and measured metrics. Two authenticated JSON endpoints use the same readers as the pages. |
| Deployment | Native Windows and Docker layouts. Compose's certificate mount disagreed with its documented setting. | Native TLS, dashboard and replay ran end to end. Compose uses configurable loopback ports, data and certificate paths. The rebuilt Linux Compose stack passed end-to-end testing. |

## Machine learning results

| Held-out AI4I metric | Original forest | Improved forest |
|---|---:|---:|
| Accuracy | 97.80% | 99.20% |
| Precision | 70.45% | 100.00% |
| Recall | 60.78% | 76.47% |
| F1 | 65.26% | 86.67% |
| ROC AUC | 96.54% | 97.08% |
| PR AUC (average precision) | 69.77% | 87.76% |

| AI4I confusion matrix | True negatives | False positives | False negatives | True positives |
|---|---:|---:|---:|---:|
| Original | 1,437 | 13 | 20 | 31 |
| Improved | 1,450 | 0 | 12 | 39 |

The AI4I dataset has 10,000 rows, 339 failures, zero duplicate model-input rows and zero missing numeric model inputs. Nine positive labels have no corresponding failure-mode flag. Identifiers and failure-mode flags were excluded from features. Both models were scored on the same held-out 1,501 rows containing 51 failures. The improved training used 6,999 rows and selected its operating threshold and algorithm using the separate 1,500-row validation split.

The selected 64-tree Random Forest uses more candidate split points, continuous leaf scores and torque times tool wear. The decision tree, unweighted forest and weighted forest tied at 86.67% validation F1 and 76.47% recall. The unweighted forest led on validation average precision at 85.10%. A separate experiment trained on the first 7,000 rows in UDI order, selected on the next 1,500 and tested on the last 1,500. It selected a decision tree and obtained 80.00% precision, 68.97% recall and 74.07% F1. The ordered result shows weaker generalisation under that split. AI4I provides concurrent labels and has no time-to-failure target or physical asset groups.

The live forecast uses weighted logistic regression with trailing means, changes and spread for temperature, vibration, pressure and current. It was trained, tuned and evaluated on disjoint simulator seeds. On 4,518 eligible test readings, accuracy was 99.20%, precision 94.66%, recall 91.85%, F1 93.23%, ROC AUC 99.92% and average precision 98.77%. The confusion matrix was 4,234 true negatives, 14 false positives, 22 false negatives and 248 true positives. The earliest warning fell within the six-reading horizon for all 45 simulated breakdowns, with a median lead of six readings, approximately 12 seconds. Per-reading evaluation excludes breakdown and immediate recovery windows by design.

The hybrid detector was also measured on a separate set of 60 synthetic episodes with 6,000 readings. It reached 88.23% precision, 49.26% recall and 63.22% F1. Counts were 3,276 true negatives, 168 false positives, 1,297 false negatives and 1,259 true positives. It found all injected spike, pressure-drop, vibration-burst and current-surge samples. Individual readings in slower drift and degradation events were harder to detect.

## System verification

- All 29 automated tests passed. They cover normal operation, temperature spikes and gradual rises, vibration bursts, pressure drops, current surges, humidity drift, simultaneous anomalies, warnings before simulated breakdown, idempotency, invalid data, SQLite persistence, alert acknowledgement and Flask views.
- Native Mosquitto, publisher, consumer and dashboard ran together. The demo database held live readings for all three machines, anomaly events, all three alert severities and live forecasts. The 100-record TLS replay produced 100 stored AI4I predictions, with three actual positives and two predicted positives. A separate 40-record SKAB TLS replay preserved all 40 original source timestamps.
- Chrome rendered the fleet overview, five Plotly charts, recent anomaly events, alert explanations, reading history, both model reports and a manual prediction. The monitoring API returned advancing timestamps for all three machines on successive requests.
- Docker Compose configuration, Linux image builds, all four service startups, and the full data path passed the follow-up verification below.

## Files

- Added `sensors/machine_simulator.py`, `dashboard/monitoring.py`, `detection/live_maintenance.py`, `detection/train_ai4i_improved.py`, `detection/train_live_maintenance.py`, `detection/evaluate_live_anomalies.py` and `detection/test_live_system.py`.
- Added `models/ai4i_improved.pkl`, `models/live_maintenance.json` and the three corresponding evaluation reports in `results/`.
- Updated `dashboard/app.py`, `detection/hybrid_detector.py`, the SKAB replay entry point, MQTT publisher, replay publisher, consumer, message contract and security modules in `messaging/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `run_tests.bat`, `.github/workflows/tests.yml` and `README.md`.

## Reproduce and run

Install with Python 3.12 from the repository root.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector detection.test_live_system -q
```

Set up Mosquitto TLS certificates and the two MQTT role passwords using the steps in [README.md](README.md). For a native setup with the broker listening on port 8883, open separate terminals in the repository root. Supply `MQTT_CONSUMER_PASSWORD` to the consumer, `MQTT_PUBLISHER_PASSWORD` to the publisher and optional replay.

```powershell
mosquitto -c C:\path\to\mosquitto.conf -v
.\venv\Scripts\python.exe -m messaging.consumer
.\venv\Scripts\python.exe -m dashboard.app
.\venv\Scripts\python.exe -m messaging.publisher
.\venv\Scripts\python.exe -m messaging.ai4i_replay_publisher --limit 100
.\venv\Scripts\python.exe -m sensors.skab_replay --limit 40
```

Open http://localhost:5000, create the dashboard account on the first visit, then sign in. The Docker path uses `docker compose config --quiet` and `docker compose up -d --build` after configuring credentials and `MQTT_SECURITY_DIR`. Native installations can use `MQTT_PORT`, `MQTT_CERT_FILE`, `IOT_DB_PATH` and `IOT_FAULT_LOG_DIR` to match local infrastructure.

```powershell
.\venv\Scripts\python.exe -m detection.train_ai4i_improved
.\venv\Scripts\python.exe -m detection.train_live_maintenance
.\venv\Scripts\python.exe -m detection.evaluate_live_anomalies
```

## Docker Compose verification

The current stack was built and exercised on Docker Desktop's Linux ARM64 engine on 26 November 2026. The Compose project `iot-maintenance-verified` is running with the dashboard on `http://localhost:5001` and the host MQTT listener on `127.0.0.1:8884`. Containers use `mqtt:8883` on their own network. Separate bind mounts keep the verification SQLite database and fault CSVs independent from the earlier stack.

| Check | Observed result |
|---|---|
| Container startup | Mosquitto, publisher, consumer and dashboard all reported `running` with zero automatic restarts after the final recreation. |
| MQTT transport | Broker logs showed authenticated publisher and consumer sessions negotiated TLS 1.3. Fresh readings continued after broker recreation. |
| SQLite | The dashboard container could read the database written by the consumer. `PRAGMA quick_check` returned `ok`, journal mode was WAL, and 266 readings across three machines had all five fields populated at the evidence snapshot. |
| Anomalies and alerts | 127 events across six categories and 45 alerts spanning Low, Medium and High. |
| Live forecast | 239 persisted forecasts, including 35 at or above threshold, produced three forecast alerts in the snapshot. |
| AI4I classifier | 100 records traversed the broker and were stored. The classifier flagged two of three labeled failures with no false positives in that replay. The same 100 predictions remained after broker recreation. |
| Browser | Chrome rendered the existing dashboard with five charts, each with 30 data points. The sensor cards matched the latest plotted values, all three timestamps advanced, and anomaly, alert, history, replay and model pages showed stored results. Registration, sign-in, a manual prediction, and sign-out also worked. The temporary verification account was removed. |
| Automated tests | All 29 tests passed inside the built Linux image. |

The initial broker rejected the current MQTT passwords because its existing password file belonged to an earlier setup. The verification stack uses separately generated role hashes matching the local Compose credentials. Mosquitto now stages the credential and ACL files in container tmpfs with mode 0600 and `mosquitto` ownership. The recreated broker logged no credential permission or authentication errors.

Evidence is in `%TEMP%\iot-compose-verification` on this workstation. It includes `docker-services.txt`, `docker-mqtt-tls.txt`, `docker-backend-verification.json`, `docker-post-recreation.json`, `docker-browser-verification.json`, `docker-unittest.log`, and Chrome screenshots. This test exercises simulated input and local deployments.

To inspect or restart the verified stack from PowerShell in the repository root:

```powershell
$composeCheck = Join-Path $env:TEMP 'iot-compose-verification'
$env:IOT_DATA_DIR = Join-Path $composeCheck 'data'
$env:MQTT_SECURITY_DIR = Join-Path $composeCheck 'security'
$env:DASHBOARD_HOST_PORT = '5001'
$env:MQTT_HOST_PORT = '8884'
docker compose -p iot-maintenance-verified ps
docker compose -p iot-maintenance-verified up -d --build
```

## Remaining limitations

Accuracy exceeded 95% on both primary model evaluations. F1, recall and generalisation across unseen physical equipment remain below or outside that claim. The live forecast learns from three simulated machine profiles, with no field telemetry or real failure histories available for validation. It provides a short-horizon maintenance signal, and the repository has no verified remaining-useful-life model. The optional outbound webhook requires a configured endpoint and was outside this local verification.
