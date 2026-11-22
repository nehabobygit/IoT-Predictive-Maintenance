# IoT-Based Predictive Maintenance System
## 1. Project Overview
This project is an IoT-based predictive maintenance prototype designed to monitor industrial equipment, detect abnormal sensor behaviour, generate maintenance alerts and support machine-failure prediction.

The system combines:

- IoT sensor simulation

- MQTT-based communication

- Real-time anomaly detection

- SQLite database storage

- Flask-based monitoring dashboard

- Maintenance alert management

- Machine-learning-based failure classification

- Dataset replay and performance evaluation

The project is intended for academic research and demonstration. It has not been validated for production deployment in an industrial environment.

---
## 2. Project Objectives
1. Monitor industrial equipment using multiple sensor readings.

2. Detect abnormal operating conditions using statistical methods.

3. Generate maintenance alerts with severity levels.

4. Provide a dashboard for monitoring equipment conditions.

5. Support maintenance acknowledgement and status tracking.

6. Predict machine failures using a trained machine-learning model.

7. Evaluate detection performance using benchmark datasets.

8. Maintain traceable sensor events and prediction records.

---
## 3. System Architecture
### A. Live Sensor Monitoring
```text

Five Simulated Sensors

         |

         v

    MQTT Publisher

         |

         v

   Mosquitto Broker

         |

         v

    MQTT Consumer

         |

         v

  Anomaly Detection

         |

         v

    SQLite Database

         |

         v

    Flask Dashboard

         |

         v

 Maintenance Actions

```

The five monitored parameters are:

| Sensor | Unit |

|---|---|

| Temperature | °C |

| Vibration | mm/s |

| Humidity | % |

| Pressure | bar |

| Current | A |

The simulated publisher generates sensor readings and introduces abnormal conditions to test the monitoring system.

### B. Machine-Failure Prediction
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

 Failure Probability

        |

        v

Normal / Failure Decision

```

The machine-learning prediction module uses AI4I machine operating parameters.

The AI4I prediction workflow and the five-sensor monitoring workflow are separate. They do not currently form one unified industrial prediction model.

---
## 4. Technologies Used
| Technology | Purpose |

|---|---|

| Python 3.12.10 | Application development |

| Flask 3.1.3 | Web dashboard |

| Paho-MQTT 2.2.0 | MQTT communication |

| Mosquitto | MQTT message broker |

| SQLite | Database storage |

| NumPy 2.5.4 | Numerical computation and machine learning |

| HTML, CSS and JavaScript | Dashboard interface |

| Git and GitHub | Version control |

The final AI4I Random Forest model uses a custom Python and NumPy implementation.

Scikit-learn is not required to load and use the final AI4I model.

### Tested Development Environment
- Windows 10 ARM64

- Python 3.12.10

- Local Mosquitto MQTT broker

- Python virtual environment

Other operating systems and Python versions have not been fully verified.

---
## 5. Sensor Simulation
The system generates five sensor measurements.

Typical simulated ranges:

| Sensor | Normal simulation range |

|---|---|

| Temperature | 35–45 °C |

| Vibration | 1–5 mm/s |

| Humidity | 30–70% |

| Pressure | 2–6 bar |

| Current | 5–20 A |

The simulation introduces conditions such as:

- Sudden temperature spikes

- Gradual temperature increases

- Vibration spikes

- Humidity drift

- Pressure drops

- Current surges

These simulated faults are used to test the monitoring and alert pipeline.

The simulated ranges are demonstration values and are not validated operating limits for a particular industrial machine.

---
## 6. Anomaly Detection
The live monitoring system uses rolling Z-score analysis.

The Z-score measures how far a sensor reading differs from the recent average relative to the standard deviation.

The current configuration uses:

| Parameter | Value |

|---|---|

| Rolling window | 10 readings |

| Z-score threshold | 1.5 |

| Alert cooldown | 30 seconds |

An anomaly is detected when the absolute Z-score exceeds the configured threshold.

### Alert Severity
| Absolute Z-score | Severity |

|---|---|

| Below 3.5, but above detection threshold | LOW |

| 3.5 to below 5.0 | MEDIUM |

| 5.0 or above | HIGH |

The system generates maintenance recommendations according to the affected sensor.

### Important Limitation
The threshold of 1.5 is an experimental configuration. It has not been established as an optimal threshold for real industrial equipment.

False alarms remain a significant limitation.

---
## 7. MQTT Communication
The monitoring system uses the following MQTT topics:

| Topic | Purpose |

|---|---|

| `factory/sensors` | Simulated sensor measurements |

| `factory/ai4i/replay` | AI4I dataset replay |

The MQTT consumer receives incoming events, validates their contents, processes readings and stores relevant information.

### Event Metadata
The updated message contract supports:

- Schema version

- Event ID

- Run ID

- Asset ID

- Data source

- Event timestamp

- Source timestamp

- Sensor units

- Source channel metadata

- Synthetic-field metadata

These fields improve traceability and help distinguish simulated readings from dataset replay events.

Duplicate event detection is supported.


### MQTT Security

The project uses authenticated MQTT communication with TLS encryption.

- MQTT TLS port: `8883`
- Broker: Mosquitto 2.1.2
- Consumer account: `maintenance_consumer`
- Publisher account: `maintenance_publisher`
- Passwords are supplied through environment variables.
- Broker ACLs restrict publishers to writing and consumers to reading.
- TLS certificates are stored locally and are not included in the repository.

The local development environment uses a self-signed TLS certificate. Each installation must configure its own broker credentials, ACL rules and trusted certificate.

The Python MQTT clients verify the broker certificate before connecting.

The unencrypted port `1883` remains available locally for compatibility and should be disabled when no longer required.

Do not commit passwords, private keys or broker authentication files.


---
## 8. Database
SQLite stores monitoring and prediction information.

The principal database tables include:

### Sensor Readings
Stores sensor values, timestamps, asset information, source information and event metadata.

### Alerts
Stores detected anomalies, severity, affected sensor, reading, recommendations and event metadata.

### Predictions
Stores AI4I machine-failure predictions, confidence scores and relevant machine information.

The project also includes database migration scripts:

- `detection/migrate_project_metadata.py`

- `detection/migrate_prediction_metadata_v2.py`

These scripts support the additional metadata fields introduced during development.

The local SQLite database is excluded from GitHub.

A fresh installation does not contain the historical monitoring data generated on the development machine.

---
## 9. Flask Dashboard
The dashboard provides the following functionality.

### Overview
Displays monitoring summaries and recent sensor conditions.

### Sensors
Displays sensor readings and charts for temperature, vibration, humidity, pressure and current.

### Alerts
Displays anomaly alerts and severity information.

### Reading History
Displays stored sensor readings.

### Prediction
Allows users to enter AI4I machine parameters and obtain a failure classification.

### Maintenance Management
The maintenance interface supports:

- Viewing maintenance alerts

- Acknowledging alerts

- Scheduling maintenance

- Updating maintenance status

- Filtering maintenance records

- Paginated record viewing

Maintenance actions use CSRF protection.

### Dashboard Security Limitation
The dashboard provides environment-configured username/password login. Role-based access control is not implemented.

It should not be exposed publicly without additional security hardening, TLS, appropriate access controls and deployment review.

---
## 10. AI4I Machine-Failure Prediction
The machine-learning component uses the AI4I 2020 Predictive Maintenance dataset.

### Dataset
| Property | Value |

|---|---|

| Total records | 10,000 |

| Training records | 6,999 |

| Validation records | 1,500 |

| Test records | 1,501 |

| Model | Custom Random Forest |

| Trees | 25 |

| Maximum depth | 8 |

| Decision threshold | 0.76 |

The model uses machine parameters including:

- Air temperature

- Process temperature

- Rotational speed

- Torque

- Tool wear

- Machine type

Additional engineered features include temperature difference and torque-speed interaction.

### Test-Set Results
| Metric | Result |

|---|---:|

| Accuracy | 97.80% |

| Precision | 70.45% |

| Recall | 60.78% |

| F1-score | 65.26% |

| True positives | 31 |

| False positives | 13 |

| False negatives | 20 |

| True negatives | 1,437 |

These results come from the held-out AI4I test split.

The model missed 20 actual failures in this test.

****High accuracy does not mean that all machine failures are detected.****

The model predicts a binary failure classification. It does not predict remaining useful life, exact failure time or expected downtime.


### Model File

The trained AI4I Random Forest model is stored at:

`models/ai4i_random_forest.pkl`

Before loading the model, the consumer and dashboard verify its SHA-256 checksum using `messaging/model_security.py`.

If the model has been modified, loading is rejected.

The expected checksum can be configured using the `AI4I_MODEL_SHA256` environment variable.

Only load model files from trusted sources. SHA-256 verification detects unexpected changes but does not make untrusted pickle files safe.

---
## 11. Benchmark Datasets
The project uses three datasets for different purposes.

### AI4I 2020
Used to train and evaluate the machine-failure classification model.

### SKAB
Used to evaluate anomaly detection using recorded industrial sensor sequences.

### NAB
Used for additional anomaly-detection experiments.

The NAB dataset is not bundled in the GitHub repository because of its size.

Dataset sources and licensing information are documented in:

`DATASET_ATTRIBUTION.md`

### Dataset Licensing
The bundled SKAB material includes GPL-3.0-licensed content.

Redistribution must comply with the applicable licence obligations.

The AI4I dataset uses CC BY 4.0 licensing, and NAB includes MIT-licensed material.

---
## 12. SKAB Anomaly Detection Evaluation
The project includes:

`detection/evaluate_skab_final.py`

This script evaluates selected SKAB sequences and compares two approaches:

1. Rolling Z-score

2. Fixed-reference detection

The evaluation includes:

- Per-sequence results

- Confusion matrices

- Precision

- Recall

- F1-score

- Accuracy

- False-positive rates

- False positives per 1,000 readings

- Anomaly episode detection

- Detection delays

### Overall Evaluation Results
| Metric | Rolling Z-score | Fixed Reference |

|---|---:|---:|

| Precision | 39.02% | 38.16% |

| Recall | 60.22% | 34.14% |

| F1-score | 47.35% | 36.04% |

| Accuracy | 48.60% | 53.48% |

| False-positive rate | 58.64% | 34.47% |

| False positives per 1,000 readings | 361.29 | 212.37 |

| Detected anomaly episodes | 3 | 2 |

| Missed anomaly episodes | 0 | 1 |

| Mean detection delay (samples) | 0.67 | 111.00 |

The evaluation uses selected sequences:

- `0.csv`

- `3.csv`

- `11.csv`

These results are not representative of all industrial machines or all SKAB sequences.

### Evaluation Conclusion
Rolling Z-score achieved better recall and episode detection than the fixed-reference approach in this evaluation.

However, both methods generated substantial false alarms.

Further calibration and validation are necessary before using the detection methods for operational maintenance decisions.

### Saved Evaluation Report
`results/skab_final_evaluation.json`

To reproduce the evaluation:

```cmd

python detection\evaluate_skab_final.py

```

---
## 13. Installation and Setup

### Prerequisites

- Python 3.12.10 (tested on Windows 10 ARM64)
- Git
- Mosquitto MQTT broker, installed separately
- Windows Command Prompt (CMD)

Other operating systems and Python versions have not been fully verified. All commands below assume you are in the **same cloned project folder**. Do not mix processes running from different clones: each clone has its own SQLite database.

### Step 1 — Clone the Repository

Copy the repository's HTTPS clone URL from GitHub and run:

```cmd
git clone <YOUR_REPOSITORY_HTTPS_URL>
cd <CLONED_PROJECT_FOLDER>
```

Replace both placeholders with your own values. The folder name is determined by the clone destination, not necessarily `IoT_Predictive_Maintenance`.

### Step 2 — Create and Activate a Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```cmd
python -m pip install -r requirements.txt
python -m pip check
```

Primary requirements: Flask 3.1.3, Paho-MQTT 2.2.0 and NumPy 2.5.4. The final custom Random Forest does not require scikit-learn.

### Step 4 — Configure and Start Mosquitto

The MQTT clients require the following broker-side accounts:

| Client role | MQTT username | Environment variable containing password |
|---|---|---|
| Consumer | `maintenance_consumer` | `MQTT_CONSUMER_PASSWORD` |
| Both publishers | `maintenance_publisher` | `MQTT_PUBLISHER_PASSWORD` |


### Local MQTT TLS Configuration

The MQTT clients connect to `localhost` on port `8883` using TLS.

Before running the application:

1. Install Mosquitto and create the `maintenance_consumer` and `maintenance_publisher` accounts.
2. Configure a local TLS listener on port `8883`.
3. Create a TLS certificate with `localhost` as a valid hostname.
4. Configure broker ACLs so publishers can write and consumers can read the required topics.
5. Place the trusted broker certificate at:

   `%USERPROFILE%\mqtt_tls\server.crt`

6. Restart Mosquitto after updating its configuration.

The certificate and broker credentials must be configured separately on each computer. They are not distributed through GitHub.

The MQTT client passwords must match the corresponding Mosquitto accounts.


**Broker configuration is separate from the Python application.** Before starting the application, configure Mosquitto with both accounts and their passwords using a Mosquitto password file and an appropriate local broker configuration. The values entered into the CMD prompts must match the broker's passwords. Do not commit the password file or passwords. The repository does not bundle broker credentials, TLS certificates or ACL files. These must be configured locally.

Start Mosquitto with the authenticated local configuration you created, for example:

```cmd
mosquitto -c <PATH_TO_YOUR_MOSQUITTO_CONFIG> -v
```

Replace the placeholder with the path to your actual configuration file. `mosquitto -v` by itself does **not** establish that authentication is enabled. Keep the broker window running. Do not expose the broker to the public internet.

### Step 5 — Start the Consumer (CMD Window 2)

Open a **new Command Prompt** (Windows + R, type `cmd`, press Enter), change into the same cloned folder and activate its environment:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_CONSUMER_PASSWORD=Enter MQTT consumer password:
python messaging\consumer.py
```

Enter the password for `maintenance_consumer`. The password is **visible as you type** in CMD. The environment variable is set only for this CMD session. Keep this window open and check for `Connected to MQTT Broker!` and subscriptions to `factory/sensors` and `factory/ai4i/replay`.

### Step 6 — Start the Simulated Sensor Publisher (CMD Window 3)

Open another CMD window in the **same cloned folder**:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
python messaging\publisher.py
```

Enter the password for `maintenance_publisher`. The publisher generates five-sensor readings and occasional simulated faults. The consumer should print saved readings and detected anomalies.

### Step 7 — Start the Dashboard (CMD Window 4)

Open another CMD window in the **same cloned folder**:

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p DASHBOARD_USERNAME=Enter dashboard username:
set /p DASHBOARD_PASSWORD=Enter dashboard password:
python dashboard\app.py
```

Set your chosen local dashboard login username and password; these are **not** the MQTT credentials. Both variables must be present in the **dashboard's own CMD session**. CMD displays values while typing. Do not share or commit credentials.

Open **http://127.0.0.1:5000** and sign in using the dashboard credentials. Check the Overview, Sensors, Alerts and Reading History pages.

### Troubleshooting

- `MQTT_CONSUMER_PASSWORD is not configured`: set that variable in the **consumer** CMD window before launching it.
- `MQTT_PUBLISHER_PASSWORD is not configured`: set that variable in **each publisher** CMD window before launching it.
- `Invalid username or password` on the dashboard: stop the dashboard with Ctrl+C, set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in that CMD window, restart and try again.
- Broker connection/authentication fails: verify Mosquitto is running, the broker accounts exist, and passwords match.
- Sensor readings appear but AI4I predictions remain at zero: run the AI4I replay (Section 14), confirm the consumer subscribes to `factory/ai4i/replay`, and make sure the **consumer and dashboard are running from the same clone**.
- A fresh clone has an empty local SQLite database until the consumer processes messages; the developer's historical database is not included.

The application is a local research prototype, not a production deployment.

---

## 14. Running Dataset Replay

Keep the authenticated Mosquitto broker and consumer running. Use a **new CMD window in the same clone** and activate its virtual environment.

### AI4I Replay (Populates Prediction Records)

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
python messaging\ai4i_replay_publisher.py
```

The replay publisher uses the `maintenance_publisher` account and publishes AI4I dataset records on `factory/ai4i/replay`. Its default replay in the clean-clone verification published 100 records. The consumer loads `models/ai4i_random_forest.pkl`, processes the records and saves predictions in the local SQLite database. Refresh the **Prediction** dashboard page to view the records. The replay publisher stops when its configured batch finishes.

### SKAB Replay

```cmd
cd /d <FULL_PATH_TO_CLONED_PROJECT>
venv\Scripts\activate
set /p MQTT_PUBLISHER_PASSWORD=Enter MQTT publisher password:
python sensors\skab_replay.py
```

SKAB replay uses recorded industrial sensor sequences. Confirm the replay script's MQTT authentication configuration before relying on it as an authenticated-broker test; this replay command has not been independently verified in the clean-clone run described below.

The AI4I replay and five-sensor monitoring streams have different message structures and processing paths. Multiple publishers can run concurrently when intentionally testing mixed data sources; each needs its own CMD session and the appropriate MQTT credentials.

---

## 15. Automated Testing
The project includes unit and integration tests. A GitHub Actions workflow (`.github/workflows/tests.yml`) also runs the automated tests on repository updates.

### Windows Test Runner
Run:

```cmd

run_tests.bat

```

### Alternative Python Command
```cmd

python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector -q

```

The test suite covers:

- Sensor event validation

- Anomaly detection

- Alert generation

- Duplicate event handling

- Alert cooldown behaviour

- Invalid readings

- Empty database handling

- AI4I feature processing

- AI4I prediction storage

- Invalid AI4I messages

The project has previously passed 21 integration tests and 7 detector tests.

These tests do not replace live MQTT broker testing, security testing or industrial validation.

---
## 16. Reproducibility

The repository includes project source code, dependency requirements, the trained AI4I model, AI4I and selected SKAB data, evaluation scripts/results, automated tests and dataset attribution documentation. The local SQLite database and historical monitoring records are not committed.

### Clean-Clone Verification (22 November 2026)

A separate clean clone on Windows 10 ARM64 / Python 3.12.10 was tested with:

- Fresh virtual environment and successful installation from `requirements.txt`
- `python -m pip check` with no broken requirements
- `run_tests.bat` passing **28 automated tests**
- Authenticated MQTT consumer receiving simulated sensor data and saving anomaly alerts
- Dashboard login working with environment-provided credentials
- AI4I replay publishing **100 records**, followed by successful prediction display after the consumer and dashboard were launched from the **same clone**

**Important reproducibility lesson:** Running the consumer from the original working folder and the dashboard from the clean clone produced empty prediction counts in the clone. Run all application processes from the same cloned folder to use the same SQLite database.

This verifies the tested local workflow, not production deployment, every dataset replay option, or industrial accuracy.

---

## 17. Security Considerations

Implemented controls include:

- MQTT message validation and duplicate event handling
- MQTT client credentials supplied through environment variables (`MQTT_CONSUMER_PASSWORD`, `MQTT_PUBLISHER_PASSWORD`)
- Dashboard login using `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`
- CSRF protection for maintenance actions
- Local SQLite storage

The consumer uses MQTT username `maintenance_consumer`; the publishers use `maintenance_publisher`. Mosquitto must be configured separately to validate those accounts. The login is basic local authentication; it is **not** role-based access control or a production identity system.


### Security Limitations

The following security controls have been implemented and locally tested:

- MQTT username/password authentication
- TLS-encrypted MQTT communication on port 8883
- Broker access-control lists (ACLs)
- SHA-256 integrity verification before loading the AI4I model
- Dashboard login authentication
- CSRF protection for maintenance actions

Remaining limitations:

- The unencrypted MQTT port 1883 remains enabled locally.
- TLS uses a locally generated self-signed certificate.
- Dashboard authentication does not support multiple user roles.
- No production security audit has been performed.

The project is intended for local academic demonstration, not production deployment.


Never commit passwords, Mosquitto password files or secret environment settings. Use the system only in a trusted development environment until these limitations are addressed.

---

## 18. Current Limitations
The main limitations are:

1. Sensor data is simulated or replayed from benchmark datasets.

2. No real industrial pilot has been completed.

3. Anomaly thresholds require further calibration.

4. SKAB testing shows high false-positive rates.

5. The AI4I model misses some actual failures.

6. The AI4I model and five-sensor monitoring system are separate.

7. The system predicts failure classification, not time-to-failure.

8. MQTT security is configured for local testing; production security hardening has not been completed.

9. Dashboard authentication is implemented for local use, but role-based access control is not.

10. Large-scale database retention and deployment behaviour have not been validated.

11. Performance has not been verified across different operating systems and industrial environments.

---
## 19. Future Improvements
Potential future work includes:

- Stronger dashboard authentication and user roles

- Industrial threshold calibration

- Reduced false-alarm rates

- MQTT reconnect and recovery testing

- Database retention and archival policies

- Real industrial sensor integration

- Unified live machine-failure prediction

- Time-to-failure estimation

- Per-machine validation

- Production deployment automation and release hardening

- Cloud-based monitoring

- Authorised industrial pilot testing

These are future improvements, not completed project features.

---
## 20. Conclusion
This project demonstrates an IoT-based predictive maintenance prototype combining simulated sensor monitoring, MQTT communication, anomaly detection, maintenance management and machine-learning-based failure classification.

It provides a working foundation for monitoring equipment behaviour and investigating abnormal operating conditions.

The AI4I model demonstrates machine-failure classification capability, while the SKAB evaluation identifies important limitations in statistical anomaly detection.

Further security hardening, threshold calibration, model validation and industrial testing are required before production deployment.
