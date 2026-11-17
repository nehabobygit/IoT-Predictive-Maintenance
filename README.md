# IoT-Based Predictive Maintenance System

## Project Overview

This project is an IoT-based predictive maintenance prototype designed to monitor industrial equipment using simulated sensor data, detect unusual operating behaviour and support maintenance decision-making.

The system collects readings from five simulated sensors, transmits them using MQTT, detects anomalies using rolling Z-score analysis, stores readings and alerts in an SQLite database, and displays the results through a Flask-based web dashboard.

It also includes a separate machine-failure classification module developed using a custom NumPy-based Random Forest model trained on the AI4I 2020 Predictive Maintenance dataset.

## Features

### 1. IoT Sensor Monitoring
- Monitoring of five simulated sensor parameters:
  - Temperature
  - Vibration
  - Humidity
  - Pressure
  - Current
- Continuous sensor-data generation.
- Simulated normal readings and fault-like changes.
- MQTT-based communication between the publisher and consumer.

### 2. Anomaly Detection
- Rolling statistical anomaly detection using Z-score analysis.
- Detection of unusual sensor behaviour.
- High, Medium and Low severity classification.
- Maintenance recommendations for detected anomalies.
- A 30-second alert cooldown for each sensor and severity level.

### 3. Web Dashboard
- Overview of sensor readings and system activity.
- Live sensor monitoring.
- Maintenance alerts with severity information.
- Historical reading records.
- Interactive graphs and visualisations.
- Filtering and pagination for alerts and reading history.
- Automatic dashboard refresh.

### 4. Machine-Failure Prediction
- Custom NumPy-based Random Forest classifier.
- Trained using the AI4I 2020 Predictive Maintenance dataset.
- Uses machine parameters to classify normal or potential failure conditions.
- Manual input through the Machine Failure Prediction dashboard page.
- Displays the failure score based on the proportion of trees voting for failure.

### 5. Dataset Replay
- SKAB dataset used for evaluating anomaly detection.
- Sensor readings from selected SKAB records can be replayed through the MQTT pipeline for testing.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language and application logic |
| NumPy | Numerical processing and custom machine-learning implementation |
| Flask | Web application and dashboard |
| MQTT / Mosquitto | Sensor-data communication |
| Paho-MQTT | Python MQTT client |
| SQLite | Storage of sensor readings and alerts |
| Plotly | Interactive graphs and visualisations |
| HTML and CSS | Dashboard interface |

The final Random Forest model is implemented using NumPy and Python rather than Scikit-learn.

## System Architecture

### Live IoT Monitoring Workflow

1. **Sensor Simulation:** Python generates temperature, vibration, humidity, pressure and current readings.
2. **MQTT Publisher:** Publishes sensor readings to the MQTT topic `factory/sensors`.
3. **MQTT Broker:** Mosquitto receives and forwards messages locally.
4. **MQTT Consumer:** Receives readings, performs anomaly detection and prepares alert records.
5. **SQLite Database:** Stores sensor readings and maintenance alerts.
6. **Flask Dashboard:** Displays sensor information, alerts, historical readings and graphs.

### Machine-Failure Prediction Workflow

1. The AI4I 2020 dataset is used to train a custom Random Forest model.
2. The trained model is saved as `models/ai4i_random_forest.pkl`.
3. An engineer opens the Machine Failure Prediction page.
4. The engineer enters the required machine parameters.
5. The saved model evaluates the inputs and combines the votes from its decision trees.
6. The dashboard displays the failure score and the corresponding classification.

**Important:** The AI4I prediction module currently operates separately from the live MQTT sensor-monitoring pipeline. Its predictions are based on manually entered machine parameters, not automatically on incoming MQTT readings.

## Machine-Learning Model

### Dataset

**AI4I 2020 Predictive Maintenance Dataset**

- Total records: 10,000
- Normal records: 9,661
- Failure records: 339

### Model Configuration

| Parameter | Configuration |
|---|---|
| Algorithm | Custom Random Forest |
| Implementation | Python and NumPy |
| Number of trees | 25 |
| Maximum tree depth | 8 |
| Training strategy | Failure-class oversampling |
| Data split | 70% training, 15% validation, 15% testing |
| Decision threshold | 0.76 |

### Input Parameters

The prediction page accepts the following six machine parameters:

- Air temperature
- Process temperature
- Rotational speed
- Torque
- Tool wear
- Machine type

Additional derived features are calculated by the model during prediction.

### Prediction Interpretation

The model calculates the proportion of decision trees voting for failure.

- Failure score below 76%: Classified as Normal.
- Failure score at or above 76%: Classified as Failure Predicted.

The displayed score represents the proportion of tree votes, not a calibrated probability of failure.

The prediction is intended as decision support and should not be treated as a guarantee of equipment failure.

## Anomaly Detection

The live monitoring system uses rolling Z-score analysis to identify unusual changes in sensor readings.

The Z-score is calculated using:

`Z = (x - μ) / σ`

Where:

- `x` = Current sensor reading
- `μ` = Mean of recent readings
- `σ` = Standard deviation of recent readings

The configured live detection threshold is 1.5.

### Alert Severity

| Severity | Absolute Z-score | Recommended Action |
|---|---|---|
| High | 5 or above | Immediate inspection |
| Medium | 3.5 to below 5 | Investigate the equipment |
| Low | Above 1.5 to below 3.5 | Continue monitoring |

A 30-second cooldown is applied separately for each sensor and severity level to reduce repeated alerts.

These thresholds are configuration values for the prototype and require further validation against industrial operating data.

## Project Structure

```text
IoT_Predictive_Maintenance/
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── fault_log.csv
│   ├── sensor_readings.db
│   ├── ai4i2020.csv
│   └── SKAB-master/
│
├── detection/
│   ├── anomaly_detector.py
│   ├── inspect_ai4i.py
│   ├── train_ai4i_rf.py
│   └── test_ai4i_model.py
│
├── messaging/
│   ├── publisher.py
│   └── consumer.py
│
├── models/
│   └── ai4i_random_forest.pkl
│
├── sensors/
│   ├── temperature.py
│   ├── vibration.py
│   ├── humidity.py
│   ├── pressure.py
│   ├── current.py
│   ├── all_sensors.py
│   └── skab_replay.py
│
├── requirements.txt
└── README.md
```

The structure above highlights the main project components. Additional experimental scripts and model files may also be present in the local development folder.

## Prerequisites

Install the following before running the project:

- Python 3
- Git (optional)
- Mosquitto MQTT Broker

Mosquitto must be installed separately because the project uses a local MQTT broker.

## Installation and Setup

### 1. Download the Project

Clone the repository using the clone URL available on GitHub:

```bash
git clone
```

Append the copied repository URL to the command.

Alternatively, download the repository as a ZIP file and extract it.

Open the project folder in VS Code or Command Prompt.

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the MQTT Broker

Install Mosquitto and start the broker.

If Mosquitto is available in your system PATH, run:

```bash
mosquitto -v
```

Keep the broker running while using the project.

The publisher and consumer connect to:

| Setting | Value |
|---|---|
| Broker | localhost |
| Port | 1883 |
| Topic | factory/sensors |

## Running the Project

Open three separate terminals in the project folder.

Activate the virtual environment in each terminal.

### Terminal 1: Start the MQTT Consumer

```bash
python messaging/consumer.py
```

The consumer receives sensor readings, performs anomaly detection and stores readings and alerts in SQLite.

It creates the database and required tables when the consumer starts.

### Terminal 2: Start the Sensor Publisher

```bash
python messaging/publisher.py
```

The publisher generates sensor readings, introduces simulated fault-like changes and sends the data to the MQTT broker.

### Terminal 3: Start the Flask Dashboard

```bash
python dashboard/app.py
```

Open the dashboard in your browser:

`http://127.0.0.1:5000`

The dashboard displays incoming sensor readings, detected anomalies, maintenance alerts and historical information.

Keep the broker, consumer, publisher and dashboard running during the live demonstration.

## Testing with SKAB Dataset

The project includes a SKAB dataset replay module for testing the live monitoring pipeline with recorded sensor data.

Run:

```bash
python sensors/skab_replay.py
```

The replay module sends selected recorded sensor readings through the MQTT pipeline.

This allows the anomaly detection component to be evaluated using recorded industrial sensor data rather than only randomly generated readings.

Avoid running the normal publisher and SKAB replay simultaneously unless intentionally testing combined inputs.

## Database

The system uses SQLite for local data storage.

The database file is:

`data/sensor_readings.db`

It stores:
- Sensor readings
- Timestamps
- Anomaly scores
- Alert severity
- Maintenance recommendations

The database and required tables are created when the MQTT consumer starts.

A fresh installation starts with an empty database. Previous readings and alerts are not included in the repository.

## Troubleshooting

### 1. MQTT Connection Refused
- Ensure Mosquitto is installed.
- Check that the MQTT broker is running.
- Verify that port 1883 is available.

### 2. No Sensor Readings on the Dashboard
- Ensure the MQTT broker is running.
- Start the consumer before the publisher.
- Check that both use the same broker address and topic.

### 3. Database or Table Not Found
- Start the MQTT consumer first.
- It creates the database and required tables.
- Then start the Flask dashboard.

### 4. Missing Python Modules

Run:

```bash
pip install -r requirements.txt
```

### 5. Machine-Failure Prediction Not Working
- Verify that `models/ai4i_random_forest.pkl` exists.
- Check that the required model dependencies are installed.
- Ensure valid machine parameters are entered.

## Current Limitations

- Sensor readings are simulated; physical industrial sensors have not been connected.
- MQTT communication currently runs locally on the development machine.
- The AI4I prediction model is separate from the live MQTT sensor stream.
- Machine parameters for AI4I prediction are entered manually.
- The AI4I dataset is a simulated predictive-maintenance dataset and does not represent data collected from a target factory.
- The model can miss actual failures; predictions should be treated as decision support rather than certainty.
- The system generates alerts and predictions but does not automatically stop machines or perform repairs.
- The dashboard is locally hosted and has not been deployed to a cloud server.
- Authentication, encrypted MQTT communication and production-level security have not been implemented.

## Future Improvements

- Integrate machine-learning predictions with an MQTT-based data pipeline using compatible machine-state inputs.
- Evaluate and reduce false-positive anomaly alerts.
- Improve sensor validation and fault detection.
- Add automated testing and stronger error handling.
- Integrate physical industrial sensors.
- Implement authentication and secure MQTT communication.
- Explore cloud deployment and industrial communication protocols.

## Note

This project demonstrates IoT-based sensor monitoring, statistical anomaly detection, maintenance alert generation and machine-failure classification.

It is a prototype intended for academic and demonstration purposes. Further integration, testing and validation using real industrial equipment are required before practical industrial deployment.

## Author

Developed as an IoT-Based Predictive Maintenance project.
