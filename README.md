
# IoT-Based Predictive Maintenance System

## Faculty Mentors

| Sl. No. | Name | E-Mail ID |
|:---:|---|---|
| 1 | Dr. J. Naveen | naveen.j@christuniversity.in |
| 2 | Dr. Rakoth Kandan Sambandam | rakoth.kandan@christuniversity.in |

## Student Team Details

| Sl. No. | Name | Register Number | Class | E-Mail ID |
|:---:|---|:---:|---|---|
| 1 | Amy Jaison | 2460326 | 6 BTCS A | amy.jaison@btech.christuniversity.in |
| 2 | Christa Fijo | 2460351 | 6 BTCS B | christa.fijo@btech.christuniversity.in |
| 3 | Neha Tresa Boby | 2460411 | 6 BTCS C | neha.tresa@btech.christuniversity.in |
| 4 | Rosepriya Franci George | 2460337 | 6 BTCS C | rosepriya.franci@btech.christuniversity.in |
| 5 | Nithin Krishna K | 2462521 | 6 BTCS IoT | nithin.krishna@btech.christuniversity.in |
| 6 | Adwaith Anilkumar | 2462503 | 6 BTCS IoT | adwaith.anilkumar@btech.christuniversity.in |

---

## 1. Project Overview

An end-to-end IoT-based predictive maintenance prototype designed to monitor industrial equipment, identify abnormal operating conditions, generate maintenance recommendations and support machine-failure classification.

The system integrates real-time sensor simulation, secure MQTT communication, hybrid anomaly detection, machine learning, persistent database storage and an interactive web dashboard.

The application also supports Docker-based deployment through four interconnected containerised services.

## 2. Key Features

- Real-time monitoring of five industrial sensor parameters.
- Hybrid anomaly detection using thresholds, historical comparisons and sustained-trend analysis.
- AI4I failure classification and short-horizon forecasts from live simulated sensor readings.
- Multi-machine monitoring and asset identification.
- Maintenance alerts with severity levels and recommendations.
- Maintenance scheduling, acknowledgement and status tracking.
- Machine status monitoring and notifications.
- Historical sensor readings and prediction records.
- Secure MQTT communication using TLS encryption.
- Role-based MQTT authentication and access control.
- Password-protected web dashboard.
- Persistent SQLite database storage.
- Docker-based application deployment.
- Automated testing and reproducible evaluation scripts.

## 3. System Architecture

```text
             Simulated Industrial Equipment
                          |
                          v
                 Five Sensor Parameters
                          |
                          v
                    MQTT Publisher
                          |
                    TLS Encryption
                          |
                          v
                   Mosquitto Broker
                          |
                          v
                    MQTT Consumer
                          |
                          v
                Hybrid Anomaly Detection
                          |
                          v
                    SQLite Database
                          |
                          v
                    Flask Dashboard
                          |
          +---------------+---------------+
          |               |               |
       Monitoring       Alerts       Maintenance
```

### Machine Learning Workflow

```text
                  AI4I 2020 Dataset
                          |
                          v
                  Data Preprocessing
                          |
                          v
                  Feature Engineering
                          |
                          v
                 Random Forest Model
                          |
                          v
                  Failure Classification
                          |
                          v
                   Dashboard Results
```

AI4I classifies concurrent failures from its operating inputs. The live five-sensor stream feeds a hybrid anomaly detector and a separately trained degradation forecast.

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.12 | Core application development |
| Flask | Web application and dashboard |
| MQTT | Sensor data communication |
| Eclipse Mosquitto | MQTT message broker |
| Paho-MQTT | MQTT client implementation |
| SQLite | Persistent data storage |
| NumPy | Numerical processing and machine learning |
| Plotly | Locally served dashboard charts |
| HTML, CSS, JavaScript | Dashboard interface |
| Random Forest | Machine-failure classification |
| Docker | Application containerisation |
| Docker Compose | Multi-container orchestration |
| TLS | Secure MQTT communication |
| Git and GitHub | Version control |

Both production models train and run with NumPy. Plotly supplies the local browser chart bundle.

## 5. Sensor Monitoring

| Sensor | Typical Simulated Range | Unit |
|---|---:|---|
| Temperature | 35-45 | °C |
| Vibration | 1-5 | mm/s |
| Humidity | 30-70 | % |
| Pressure | 2-6 | bar |
| Electrical Current | 5-20 | A |

The publisher sends five readings for each of three machines every two seconds. Their load cycles affect temperature, current, pressure and vibration. Staggered scenarios include spikes, gradual heating, humidity drift in both directions, concurrent faults and progressive degradation.

### Simulated Fault Conditions

- Sudden temperature spikes.
- Gradual temperature increases.
- Irregular vibration.
- Sustained humidity drift.
- Pressure drops.
- Electrical current surges.

The hybrid detector combines direct thresholds, recent-history comparisons and sustained-trend checks.

Detected anomalies are processed to generate severity levels and sensor-specific maintenance recommendations.

## 6. MQTT Communication

The application uses authenticated MQTT communication with TLS encryption on port 8883.

### MQTT Topics

| Topic | Purpose |
|---|---|
| factory/sensors | Simulated sensor readings |
| factory/ai4i/replay | AI4I machine-record replay |

### MQTT Access Control

| User | Permission |
|---|---|
| maintenance_publisher | Publish sensor and replay data |
| maintenance_consumer | Subscribe to sensor and replay data |

Each sensor event includes traceability information such as:

- Asset ID
- Event ID
- Run ID
- Data source
- Timestamp
- Sensor units
- Schema version
- Synthetic-field metadata
- Source-channel information

## 7. Dashboard Modules

| Module | Description |
|---|---|
| Overview | Equipment status and monitoring summary |
| Live Sensors | Near-real-time sensor visualisation |
| Maintenance Alerts | Anomalies, severity and recommendations |
| Reading History | Historical sensor measurements |
| Machine Failure Prediction | Manual machine-failure classification |
| Replay Prediction Results | Stored AI4I replay predictions |
| Maintenance Management | Maintenance scheduling and status tracking |
| Notifications | Monitoring and maintenance notifications |

Multi-machine filtering supports asset-specific monitoring and helps distinguish readings from different data sources.

## 8. Docker Deployment

The application has been successfully containerised and tested locally using Docker Desktop and Docker Compose.

### Docker Architecture

```text
                 Docker Compose Network
+--------------------------------------------------+
|                                                  |
|  Publisher -----> MQTT Broker -----> Consumer    |
|                       TLS                |        |
|                                          v        |
|                                    SQLite Data   |
|                                          |        |
|                                          v        |
|                                    Dashboard     |
|                                                  |
+------------------------------------------|-------+
                                           |
                                           v
                                http://localhost:5000
```

### Docker Services

| Container | Responsibility |
|---|---|
| mqtt | Secure Mosquitto MQTT broker |
| publisher | Sensor simulation and fault generation |
| consumer | Data ingestion and anomaly detection |
| dashboard | Flask monitoring application |

The publisher, consumer and dashboard share persistent project data through Docker bind mounts.

Compose binds the dashboard and MQTT host ports to localhost. Set DASHBOARD_HOST_PORT and MQTT_HOST_PORT to run alongside native services. Set IOT_DATA_DIR to use a separate writable data directory. Include data/ai4i2020.csv in that directory if you plan to replay AI4I records. MQTT_SECURITY_DIR identifies the Windows or Linux directory containing your certificates, password file and ACL.

### Deployment Verification

Local Docker testing confirmed:

- Successful application image builds.
- All four containers running.
- Authenticated MQTT communication.
- TLS-encrypted broker connections.
- Continuous simulated sensor publishing.
- Live dashboard updates.
- Database ingestion and maintenance alerts.
- Successful dashboard authentication.

The deployment was tested on Windows ARM64 using Docker Desktop with WSL 2.

## 9. Running the Project Using Docker

### 9.1 Prerequisites

- Git
- Docker Desktop with Docker Compose
- WSL 2 for the Windows Docker Desktop setup
- MQTT TLS certificates and authentication files

Ensure Docker Desktop is running before executing the commands.

### 9.2 Clone the Repository

Copy the repository HTTPS URL from GitHub.

```cmd
git clone <YOUR_REPOSITORY_HTTPS_URL>
cd <CLONED_PROJECT_FOLDER>
```

### 9.3 Verify Docker Installation

```cmd
docker --version
docker compose version
docker info
```

### 9.4 Configure MQTT Security

Create a folder named `docker_mqtt_security` in the cloned project directory, or use a separate local security directory.

The security directory must contain:

```text
docker_mqtt_security/
    server.crt
    server.key
    project_passwords.txt
    project_acl.txt
```

Generate a TLS certificate and private key using OpenSSL or another compatible certificate-generation utility.

The certificate must include `mqtt` as a valid DNS name because the Python containers communicate with the broker using its Docker service name.

For example, using OpenSSL:

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 -keyout server.key -out server.crt -subj "/CN=mqtt" -addext "subjectAltName=DNS:mqtt,DNS:localhost,IP:127.0.0.1"
```

Create the MQTT password file using the Mosquitto password utility.

```cmd
mosquitto_passwd -c project_passwords.txt maintenance_publisher
mosquitto_passwd project_passwords.txt maintenance_consumer
```

Choose independent passwords for both accounts.

Create `project_acl.txt` with the following content:

```text
user maintenance_publisher
topic write factory/sensors
topic write factory/ai4i/replay

user maintenance_consumer
topic read factory/sensors
topic read factory/ai4i/replay
```

Ensure the Mosquitto container can read the required security files while keeping the private key and credentials protected.

The supplied `docker/mosquitto.conf` defines the broker configuration.

For an external security directory, specify its location:

```cmd
set "MQTT_SECURITY_DIR=<FULL_PATH_TO_SECURITY_FOLDER>"
```

If this variable is not specified, Docker Compose uses the project's `docker_mqtt_security` directory.

### 9.5 Configure Application Credentials

In Windows CMD, enter:

```cmd
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
set /p MQTT_CONSUMER_PASSWORD=Enter MQTT consumer password:
```

The MQTT passwords must match the accounts created in the Mosquitto password file.

Create the dashboard account in the browser after startup.

These credentials are local configuration values and must not be committed to GitHub.

### 9.6 Build and Start the Application

```cmd
docker compose config --quiet
docker compose up -d --build
```

### 9.7 Verify Running Containers

```cmd
docker compose ps
```

The expected services are:

```text
mqtt
publisher
consumer
dashboard
```

All four services should display an Up status.

Check broker communication and sensor publishing:

```cmd
docker compose logs --tail=10 mqtt
docker compose logs --tail=10 publisher
```

Successful authentication and continuously published sensor messages indicate that the streaming components are operating.

### 9.8 Access the Dashboard

Open the following address in a web browser:

http://localhost:5000

On the first visit, click **Create an account**, choose a username and password, then sign in. The account persists in SQLite and setup closes once it is created.

Navigate to Live Sensors, Reading History and Maintenance Alerts to observe incoming sensor data.

### 9.9 Docker Management Commands

| Command | Purpose |
|---|---|
| docker compose up -d | Start the application |
| docker compose up -d --build | Rebuild and start |
| docker compose ps | Check container status |
| docker compose logs --tail=20 | View recent logs |
| docker compose restart | Restart services |
| docker compose down | Stop and remove containers |

The local SQLite data directory remains on the host computer when containers are stopped or removed.

## 10. Alternative Installation: Windows Without Docker

The application can also be executed directly using Python and Mosquitto.

### 10.1 Prerequisites

- Python 3.12
- Git
- Eclipse Mosquitto
- Windows Command Prompt

### 10.2 Install Dependencies

```cmd
git clone <YOUR_REPOSITORY_HTTPS_URL>
cd <CLONED_PROJECT_FOLDER>
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 10.3 Configure Mosquitto

Configure a TLS-enabled Mosquitto listener on port 8883.

Create the following MQTT accounts:

- maintenance_publisher
- maintenance_consumer

Configure the corresponding topic access permissions described in Section 9.4.

Place the trusted broker certificate at:

```text
%USERPROFILE%\mqtt_tls\server.crt
```

The certificate must be valid for localhost.

Start Mosquitto using the configured broker file:

```cmd
mosquitto -c <PATH_TO_YOUR_MOSQUITTO_CONFIG> -v
```

Alternatively, use an existing correctly configured Mosquitto Windows service.

### 10.4 Start the Consumer

Open CMD window 1 in the project folder:

```cmd
venv\Scripts\activate
set /p MQTT_CONSUMER_PASSWORD=Enter MQTT consumer password:
python -m messaging.consumer
```

Keep this window running.

### 10.5 Start the Publisher

Open CMD window 2 in the same project folder:

```cmd
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
python -m messaging.publisher
```

Keep this window running.

### 10.6 Start the Dashboard

Open CMD window 3 in the same project folder:

Open a fresh CMD window and start the dashboard:

```cmd
venv\Scripts\activate
python -m dashboard.app
```

Open:

http://localhost:5000

On the first visit, click **Create an account**, choose a username and password, then sign in. The account persists in SQLite and setup closes once it is created.

The broker, consumer and publisher must remain running to generate new live readings. Monitoring pages reload every five seconds. For a non-default native broker, set MQTT_HOST and MQTT_PORT in both MQTT processes. MQTT_CERT_FILE selects the trust certificate, IOT_DB_PATH selects the shared database for the consumer and dashboard, and IOT_FAULT_LOG_DIR redirects simulation fault CSVs.

Authenticated requests to /api/monitoring return each machine's latest five readings, UTC timestamp, status, anomalies and forecast. Pass ?asset=SIM-MOTOR-001 to filter. /api/model-performance returns the two model evaluation reports.

### 10.7 Optional AI4I Replay

With the native Mosquitto broker and consumer running, open another CMD window:

```cmd
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
python -m messaging.ai4i_replay_publisher
```

Refresh the Replay Prediction Results page to view stored predictions.

The Machine Failure Prediction page also supports manual operating-parameter inputs.

## 11. Datasets

| Dataset | Application |
|---|---|
| Simulated sensor data | Live monitoring and controlled fault injection |
| AI4I 2020 | Machine-failure classification |
| SKAB | Industrial anomaly-detection experiments |
| NAB | Time-series anomaly-detection experiments |

Dataset provenance and redistribution information are provided in `DATASET_ATTRIBUTION.md`.

The datasets support evaluation of different aspects of the predictive maintenance system.

## 12. Machine Learning and Evaluation

| Evaluation | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| [AI4I failure classification](results/ai4i_improved_metrics.json) | 99.20% | 100.00% | 76.47% | 86.67% |
| [Simulator anomaly detection](results/simulator_grouped_metrics.json) | 82.12% | 90.75% | 66.85% | 76.99% |
| [Live simulator breakdown forecast](results/live_maintenance_metrics.json) | 99.20% | 94.66% | 91.85% | 93.23% |
| [SKAB recorded anomaly detection](results/skab_grouped_metrics.json) | 55.34% | 43.86% | 71.46% | 54.36% |

Each row measures a different task on its own test set. Recall is the share of actual positive cases detected, so report it separately for each task.

- **AI4I failure classification** detected 39 of 51 failures with zero false positives. It missed 12 failures. An always-normal classifier already achieves 96.60% accuracy on this imbalanced test set.
- **Simulator anomaly detection** detected all 534 labeled episodes at least once. Its 66.85% recall measures individual readings, including 890 missed anomalous readings.
- **Live simulator breakdown forecasting** warned before all 45 test breakdowns, with a median lead of six samples (about 12 seconds). These results use simulated equipment.
- **SKAB recorded anomaly detection** detected 17 of 18 episodes. Its 43.86% precision indicates that most flagged readings were false positives. The final groups were separate from tuning in this evaluation and had been examined in earlier project experiments.

### AI4I comparison

| AI4I held-out metric | Original forest | Improved forest |
|---|---:|---:|
| Accuracy | 97.80% | 99.20% |
| Precision | 70.45% | 100.00% |
| Recall | 60.78% | 76.47% |
| F1 | 65.26% | 86.67% |
| ROC AUC | 96.54% | 97.08% |
| PR AUC (average precision) | 69.77% | 87.76% |

The improved classifier uses 64 NumPy CART trees, finer split search, leaf scores, and torque times tool wear. The original and improved models use the same stratified 6,999 / 1,500 / 1,501 split. A decision tree, a forest and a weighted forest were compared on validation F1, recall and average precision. On the test split, the improved model produced 1,450 true negatives, zero false positives, 12 false negatives and 39 true positives. A separately trained UDI-ordered experiment achieved 74.07% F1 on the final 1,500 rows.

The live model uses weighted logistic regression on the trailing ten readings to forecast a simulated breakdown within six samples, approximately 12 seconds. It uses recent means, changes between five-reading windows and recent spread for temperature, vibration, pressure and current. On 60 independently seeded test episodes, it reached 99.20% accuracy, 94.66% precision, 91.85% recall and 93.23% F1. It warned before all 45 simulated breakdowns, with a median lead of six samples.

Reproduce the evaluations from the repository root:

```cmd
python -m detection.train_ai4i_improved
python -m detection.train_live_maintenance
python -m detection.evaluate_live_anomalies
```

The default classifier is models/ai4i_improved.pkl. Its expected SHA-256 is recorded in messaging/model_security.py. If a local retraining run produces a different hash, set AI4I_IMPROVED_SHA256 to the hash you calculated for your trusted output before starting the dashboard and consumer. The dashboard reads the evaluation JSON generated by each trainer.

## 13. Hybrid Anomaly Detection Evaluation

The rules detect temperature excursions, irregular vibration, pressure deviation, current surges and humidity drift. Each detected anomaly stores its category, severity and reason. Repeated alerts for the same machine, sensor and severity observe a 30-second cooldown. Acknowledgement is tracked separately.

On an earlier 6,000-reading simulator benchmark, the rules achieved 88.23% precision, 49.26% recall and 63.22% F1. They detected every isolated temperature spike, pressure drop, vibration burst and current surge in those episodes. Sustained drift and degradation have lower reading-level recall. The forecast has its own labels and evaluation. See results/live_anomaly_metrics.json for counts.

With a trailing cross-sensor degradation rule, simulator F1 reached 76.99% versus 64.46% for the prior hybrid on the same new 6,000-reading test. The earlier hybrid and SKAB reports remain in results/ for historical comparison. They use different streams and protocols.

## 14. Database and Data Management

SQLite provides persistent storage for:

- Sensor readings.
- Anomaly events with triggered rules and severity.
- Live maintenance forecasts with scores, thresholds and horizons.
- Maintenance alerts.
- Machine-failure predictions.
- Alert acknowledgements.
- Maintenance tasks and status records.

Asset identifiers, source metadata, timestamps and run identifiers support data traceability.

The project also includes database backup functionality.

The local database is excluded from GitHub to avoid distributing machine-specific operational history.

## 15. Security Implementation

The application incorporates:

- MQTT username and password authentication.
- TLS-encrypted MQTT communication.
- Topic-level access control.
- Independent publisher and consumer permissions.
- Dashboard authentication.
- CSRF protection for maintenance actions.
- SHA-256 integrity verification of the saved AI4I model.
- Local environment-based credential configuration.
- Docker network isolation and loopback-bound host ports.
- Git and Docker exclusion rules for sensitive files.

Passwords, TLS private keys and local database files are not intended for repository distribution.

The dashboard is served over HTTP for local demonstration, while MQTT communication uses TLS encryption.

## 16. Testing and Validation

The project includes automated tests for sensor processing, anomaly detection and AI4I integration.

Run:

```cmd
run_tests.bat
```

Alternatively:

```cmd
python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector detection.test_live_system detection.test_review_workflow -q
```

A clean-clone verification conducted on 22 November 2026 reported:

- 28 passing automated tests.
- Successful authenticated MQTT sensor ingestion.
- Successful dashboard sign-in.
- Successful AI4I replay of 100 records.

The 26 November update was verified against a native TLS broker and Chrome. The same four-service stack was also rebuilt and tested in Docker Desktop on Linux ARM64. See PROJECT_AUDIT.md for browser, database, TLS and model evidence.

## 17. Project Structure

```text
IoT_Predictive_Maintenance/
|
|-- dashboard/
|   |-- app.py
|
|-- messaging/
|   |-- publisher.py
|   |-- consumer.py
|   |-- mqtt_security.py
|   |-- message_contract.py
|   |-- ai4i_replay_publisher.py
|
|-- detection/
|   |-- Training scripts
|   |-- Evaluation scripts
|   |-- Automated tests
|
|-- sensors/
|   |-- Sensor replay scripts
|
|-- data/
|   |-- Datasets
|   |-- Local database
|
|-- models/
|   |-- Trained machine learning model
|
|-- results/
|   |-- Evaluation reports
|
|-- docker/
|   |-- mosquitto.conf
|
|-- Dockerfile
|-- docker-compose.yml
|-- .dockerignore
|-- .gitignore
|-- requirements.txt
|-- run_tests.bat
|-- DATASET_ATTRIBUTION.md
|-- README.md
```

## 18. Troubleshooting

| Problem | Recommended Check |
|---|---|
| Docker is not running | Start Docker Desktop |
| Port 8883 is unavailable | Check for another running MQTT broker |
| MQTT authentication fails | Verify account passwords and broker password file |
| TLS connection fails | Verify certificate validity and mounted certificate paths |
| First dashboard sign-in | Create the account from the link on the sign-in page |
| Sensor readings are not changing | Verify publisher, consumer and broker status |
| Dashboard has no history | Generate readings after starting a fresh installation |
| Replay predictions are missing | Run the AI4I replay with the consumer active |

Use HTTP rather than HTTPS when opening the local dashboard.

## Consolidated review and operating commands

See [the consolidated tracker](CONSOLIDATED_REVIEW_COMPLETION_TRACKER.md) and [the final report](FINAL_CONSOLIDATED_PROJECT_COMPLETION_REPORT.md) for the review mapping, measured results and acceptance evidence. The reference Docker deployment uses an isolated Compose project so it can run alongside existing native installations.

### Dashboard accounts and roles

The first account created from the sign-in page is the administrator. An administrator with host or Docker access provisions individually named operator and viewer accounts. Operators can acknowledge alerts and create, reassign and complete maintenance tasks. Viewers can read the dashboard and histories. Each new maintenance task requires an alert ID and derives its asset and default recommendation from that alert. The maintenance audit records the authenticated actor and changes.

```powershell
docker compose exec dashboard python -m dashboard.accounts engineer_a operator
docker compose exec dashboard python -m dashboard.accounts observer viewer
```

Native deployments use the same module and `IOT_DB_PATH` as the running dashboard. Set `DASHBOARD_TLS_CERT` and `DASHBOARD_TLS_KEY` to run the native application over HTTPS. Use a trusted certificate for the hostname. For a reverse proxy over HTTPS, set `DASHBOARD_SECURE_COOKIE=1`. Set `DASHBOARD_SECRET_KEY` from a protected, persistent setting in shared deployments. The Compose dashboard publishes to loopback and Flask debugging is disabled.

### Compose health, replay and recovery

```powershell
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 140
docker compose ps
docker compose exec publisher python -m messaging.ai4i_replay_publisher --limit 100 --interval 0.02
docker compose exec publisher python -m sensors.skab_replay --limit 40 --interval 0.02
```

The default data mount is `./data`. In an isolated data directory, copy `ai4i2020.csv` and the upstream `SKAB-master/data/valve1/` folder there before replay. MQTT clients take `MQTT_HOST`, `MQTT_PORT`, `MQTT_CONNECT_TIMEOUT`, `MQTT_CERT_FILE` and the corresponding role password. `MQTT_CONSUMER_CLIENT_ID` identifies the subscriber session. When running multiple separate consumers against one broker, use unique client IDs. Mosquitto saves subscriber state in the `mqtt-state` named volume. QoS 1 with stable event IDs permits redelivery and application deduplication. Publisher-process exits can lose a pending message held only in memory.

Use `IOT_ASSET_REGISTRY` to supply a JSON object mapping additional asset IDs to objects with `name`, `kind`, and `source` fields. The bundled simulator and SKAB replay entries are reserved. Use an existing producer and configure its exact source and units. In Compose, place a registry file in the data mount and use its container path, for example /app/data/assets.json. The authenticated `/api/assets` endpoint shows the resulting registry.

### Backup and restore

Run an on-demand backup with the same mounted data path as the dashboard. The no-option command performs a backup every 24 hours and retains seven automatic snapshots. Run it as a supervised process, or schedule the one-shot command in your operating system. Keep backup access restricted because the SQLite snapshot includes dashboard account hashes.

```powershell
docker compose exec dashboard python -m detection.auto_backup --once
docker compose exec dashboard python -m detection.auto_backup --restore /app/data/backups/<snapshot>.db /app/data/restore-test.db
```

Replace `<snapshot>` with the filename printed by the backup command. Restore uses an exclusive new path and verifies SQLite integrity. `IOT_DB_PATH` selects the native source database. Backups and restore tests can run while normal ingestion continues.

### Evaluation reports

```powershell
python -m detection.audit_ai4i_misses
python -m detection.evaluate_simulator_grouped
python -m detection.evaluate_skab_grouped
```

The previous 418-reading simulator result and earlier 6,000-reading benchmark are historical reference results. The new simulator comparison uses whole seed sessions and the SKAB comparison uses separate sequence groups. The SKAB report includes labeled fixture provenance, event results and false alarms normalized to an eight-hour shift. See [dataset terms and attribution](DATASET_ATTRIBUTION.md).

## 19. Industrial Applications

The proposed system demonstrates potential applications in:

- Manufacturing equipment monitoring.
- Industrial motor condition monitoring.
- Equipment maintenance planning.
- Early identification of abnormal operating conditions.
- Reduction of unnecessary maintenance alerts.
- Asset-specific monitoring.
- Data-driven maintenance decision-making.

## 20. Future Scope

Potential extensions include:

- Integration with physical industrial IoT sensors.
- Cloud-based application deployment.
- Integration with industrial maintenance management platforms.
- Larger-scale multi-asset monitoring.
- Further model validation using independent industrial datasets.
- Improved failure forecasting and remaining useful life estimation.

## 21. Conclusion

The IoT-Based Predictive Maintenance System demonstrates an integrated workflow combining secure IoT communication, real-time equipment monitoring, hybrid anomaly detection, machine learning and maintenance management.

The updated AI4I classifier achieved 86.67% held-out F1. The live model reached 93.23% F1 on independent simulator episodes.

Docker-based deployment provides a structured multi-container architecture for running the application locally.

The project combines practical software engineering, data analytics, IoT communication, cybersecurity and machine learning to support intelligent industrial maintenance.
