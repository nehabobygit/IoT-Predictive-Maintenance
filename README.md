
# IoT-Based Predictive Maintenance System

## 1. Project Overview

An end-to-end IoT-based predictive maintenance prototype designed to monitor industrial equipment, identify abnormal operating conditions, generate maintenance recommendations and support machine-failure classification.

The system integrates real-time sensor simulation, secure MQTT communication, hybrid anomaly detection, machine learning, persistent database storage and an interactive web dashboard.

The application also supports Docker-based deployment through four interconnected containerised services.

## 2. Key Features

- Real-time monitoring of five industrial sensor parameters.
- Hybrid anomaly detection using thresholds, historical comparisons and sustained-trend analysis.
- Machine-failure classification using a custom Random Forest model.
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

The AI4I failure-classification workflow is separate from the live five-sensor anomaly-detection workflow.

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
| HTML, CSS, JavaScript | Dashboard interface |
| Random Forest | Machine-failure classification |
| Docker | Application containerisation |
| Docker Compose | Multi-container orchestration |
| TLS | Secure MQTT communication |
| Git and GitHub | Version control |

The custom Random Forest implementation does not require scikit-learn at runtime.

## 5. Sensor Monitoring

| Sensor | Typical Simulated Range | Unit |
|---|---:|---|
| Temperature | 35-45 | °C |
| Vibration | 1-5 | mm/s |
| Humidity | 30-70 | % |
| Pressure | 2-6 | bar |
| Electrical Current | 5-20 | A |

The sensor publisher generates normal operating readings and intentionally introduces abnormal conditions to demonstrate equipment monitoring.

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
set /p DASHBOARD_USERNAME=Enter dashboard username:
set /p DASHBOARD_PASSWORD=Enter dashboard password:
```

The MQTT passwords must match the accounts created in the Mosquitto password file.

The dashboard credentials can be chosen independently.

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

Sign in using the dashboard credentials configured earlier.

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

```cmd
venv\Scripts\activate
set "DASHBOARD_USERNAME=admin"
set /p DASHBOARD_PASSWORD=Enter dashboard password:
python -m dashboard.app
```

Open:

http://localhost:5000

Sign in using the configured dashboard credentials.

The broker, consumer and publisher must remain running to generate new live readings.

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

## 12. Machine Learning Model

The AI4I failure-classification model uses a custom Python and NumPy Random Forest implementation.

### Model Configuration

| Parameter | Value |
|---|---:|
| Total dataset records | 10,000 |
| Training records | 6,999 |
| Validation records | 1,500 |
| Testing records | 1,501 |
| Number of trees | 25 |
| Maximum tree depth | 8 |
| Classification threshold | 0.76 |

The model evaluates operating conditions using machine parameters and engineered features.

### Held-Out Test Results

| Evaluation Metric | Result |
|---|---:|
| Accuracy | 97.80% |
| Precision | 70.45% |
| Recall | 60.78% |
| F1-score | 65.26% |

### Confusion Matrix

| Actual / Predicted | Normal | Failure |
|---|---:|---:|
| Normal | 1,437 | 13 |
| Failure | 20 | 31 |

The dashboard displays the Random Forest voting score as an indication of failure risk. This score is not a calibrated failure probability.

## 13. Hybrid Anomaly Detection Evaluation

The hybrid anomaly detector was evaluated against a rolling Z-score baseline using a fixed historical simulated-sensor test run containing 418 readings.

### Performance Comparison

| Metric | Z-Score Baseline | Hybrid Detector |
|---|---:|---:|
| Precision | 45.98% | 87.05% |
| Recall | 68.18% | 68.75% |
| F1-score | 54.92% | 76.83% |
| False Positives | 141 | 18 |

### Key Improvements

- Precision increased by 41.07 percentage points.
- F1-score increased by 21.91 percentage points.
- False positives decreased by approximately 87.23%.
- Recall improved while false alerts were substantially reduced.
- Targeted tests for gradual temperature increases and sustained humidity drift passed.

These improvements demonstrate more reliable anomaly identification on the evaluated simulated-sensor run.

Fixed run IDs support reproducibility of the comparison. The historical run is not independently established as an untouched holdout dataset.

### Evaluation Commands

```cmd
python -m detection.evaluate_hybrid
python detection\evaluate_skab_final.py
```

Saved evaluation reports include:

```text
results/hybrid_evaluation.json
results/skab_final_evaluation.json
```

## 14. Database and Data Management

SQLite provides persistent storage for:

- Sensor readings.
- Detected anomalies.
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
python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector -q
```

A clean-clone verification conducted on 22 November 2026 reported:

- 28 passing automated tests.
- Successful authenticated MQTT sensor ingestion.
- Successful dashboard sign-in.
- Successful AI4I replay of 100 records.

Additional local Docker verification conducted on 25 November 2026 confirmed successful container execution and live monitoring functionality using the manually configured security environment.

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
| Dashboard login fails | Check dashboard environment variables |
| Sensor readings are not changing | Verify publisher, consumer and broker status |
| Dashboard has no history | Generate readings after starting a fresh installation |
| Replay predictions are missing | Run the AI4I replay with the consumer active |

Use HTTP rather than HTTPS when opening the local dashboard.

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

The evaluated hybrid detector achieved 87.05% precision and substantially reduced false positives compared with the rolling Z-score baseline. The AI4I Random Forest achieved 97.80% accuracy on its held-out classification test.

Docker-based deployment provides a structured multi-container architecture for running the application locally.

The project combines practical software engineering, data analytics, IoT communication, cybersecurity and machine learning to support intelligent industrial maintenance.
