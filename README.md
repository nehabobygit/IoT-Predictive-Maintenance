
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

The project includes MQTT client security helpers for environment-based credentials.

However:

- Broker authentication requires separate configuration.
- TLS encryption is not yet configured.
- Broker access-control lists are not included in the repository.
- The system is intended to run in a trusted local development environment.

Do not expose an unsecured MQTT broker to the public internet.

Do not commit passwords, authentication files or environment secrets.

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

The dashboard does not currently provide user login or role-based access control.

It should not be exposed publicly without appropriate access protection.

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

**High accuracy does not mean that all machine failures are detected.**

The model predicts a binary failure classification. It does not predict remaining useful life, exact failure time or expected downtime.

### Model File

`models/ai4i_random_forest.pkl`

The saved model is loaded for prediction.

Python pickle files must only be loaded from trusted sources. Model integrity verification has not yet been implemented.

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

Install:

- Python 3.12.10
- Git
- Mosquitto MQTT Broker

The following instructions are intended for Windows Command Prompt.

### Step 1 — Clone the Repository

Open the GitHub repository, select **Code**, and copy the HTTPS clone URL.

Run:

```cmd
git clone <YOUR_REPOSITORY_HTTPS_URL>
```

Replace the placeholder with the repository's actual HTTPS clone URL.

Then open the cloned project folder:

```cmd
cd IoT_Predictive_Maintenance
```

### Step 2 — Create a Virtual Environment

```cmd
python -m venv venv
```

Activate it:

```cmd
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```cmd
python -m pip install -r requirements.txt
```

The primary Python dependencies are:

```text
Flask==3.1.3
paho-mqtt==2.2.0
numpy==2.5.4
```

Mosquitto must be installed separately.

### Step 4 — Start the MQTT Broker

For local development, start Mosquitto using an appropriate local broker configuration.

For example, when the executable is available on PATH:

```cmd
mosquitto -v
```

Broker authentication and network access depend on the local Mosquitto configuration.

### Step 5 — Start the MQTT Consumer

Open another terminal, activate the virtual environment and run:

```cmd
python messaging\consumer.py
```

### Step 6 — Start the Sensor Publisher

Open another terminal and run:

```cmd
python messaging\publisher.py
```

The publisher generates simulated sensor readings and sends them through MQTT.

### Step 7 — Start the Dashboard

Open another terminal and run:

```cmd
python dashboard\app.py
```

Open:

http://127.0.0.1:5000

The dashboard should display the locally stored monitoring information.

### Important

Start the MQTT broker before starting the consumer and publisher.

A fresh installation begins with an empty local database.

The project is designed for local demonstration rather than unrestricted public hosting.

---

## 14. Running Dataset Replay

### SKAB Replay

```cmd
python sensors\skab_replay.py
```

This sends recorded SKAB sensor data through the MQTT pipeline.

### AI4I Replay

```cmd
python messaging\ai4i_replay_publisher.py
```

This publishes AI4I records for prediction processing.

The AI4I replay and the five-sensor monitoring stream use different message structures and processing paths.

Avoid running multiple publishers simultaneously unless intentionally testing mixed data sources.

---

## 15. Automated Testing

The project includes unit and integration tests.

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

The repository contains:

- Project source code
- Python dependency requirements
- Trained AI4I Random Forest model
- AI4I dataset
- SKAB dataset files
- Evaluation scripts
- Evaluation results
- Automated tests
- Dataset attribution documentation

The development environment uses Python 3.12.10.

A clean-clone installation and complete end-to-end reproduction should be verified separately.

The project does not include the developer's local SQLite database or historical monitoring records.

---

## 17. Security Considerations

The current implementation includes:

- MQTT message validation
- Duplicate event handling
- Environment-based MQTT credential support
- CSRF protection for maintenance actions
- Local database storage

Security limitations include:

- No dashboard user authentication
- No role-based access control
- No configured MQTT TLS encryption
- No bundled production broker ACL configuration
- No cryptographic integrity verification for pickle models
- No completed production security audit

The system should be used only in a trusted development environment until these limitations are addressed.

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
8. Production MQTT security is incomplete.
9. Dashboard authentication is not implemented.
10. Large-scale database retention and deployment behaviour have not been validated.
11. Performance has not been verified across different operating systems and industrial environments.

---

## 19. Future Improvements

Potential future work includes:

- MQTT TLS encryption and broker ACLs
- Dashboard authentication and user roles
- Secure model integrity verification
- Industrial threshold calibration
- Reduced false-alarm rates
- MQTT reconnect and recovery testing
- Database retention and archival policies
- Real industrial sensor integration
- Unified live machine-failure prediction
- Time-to-failure estimation
- Per-machine validation
- Continuous integration and deployment
- Cloud-based monitoring
- Authorised industrial pilot testing

These are future improvements, not completed project features.

---

## 20. Conclusion

This project demonstrates an IoT-based predictive maintenance prototype combining simulated sensor monitoring, MQTT communication, anomaly detection, maintenance management and machine-learning-based failure classification.

It provides a working foundation for monitoring equipment behaviour and investigating abnormal operating conditions.

The AI4I model demonstrates machine-failure classification capability, while the SKAB evaluation identifies important limitations in statistical anomaly detection.

Further security hardening, threshold calibration, model validation and industrial testing are required before production deployment.
