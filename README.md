# IoT-Based Predictive Maintenance System

## Project Overview

This project is an IoT-based predictive maintenance system designed to monitor industrial equipment using simulated sensor data.

It collects readings from five sensors, detects unusual behaviour using statistical anomaly detection, generates maintenance alerts, and displays the results through a web-based dashboard.

## Features

- Real-time monitoring of five sensors:
  - Temperature
  - Vibration
  - Humidity
  - Pressure
  - Current
- Simulated normal and faulty sensor readings
- Automatic anomaly detection using Z-score analysis
- High, Medium, and Low severity classification
- Maintenance recommendations for detected anomalies
- MQTT-based communication
- SQLite database for storing sensor readings and alerts
- Interactive dashboard with graphs, summaries, filters, and reading history
- Automatic dashboard refresh

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Flask | Web dashboard |
| MQTT / Mosquitto | Sensor data communication |
| Paho-MQTT | Python MQTT client |
| SQLite | Database |
| Pandas and NumPy | Data processing |
| Scikit-learn | Machine learning support |
| Plotly | Interactive visualizations |
| HTML and CSS | Dashboard interface |

## Project Structure

```text
IoT_Predictive_Maintenance/
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── fault_log.csv
│   └── SKAB-master/
│
├── detection/
│
├── messaging/
│   ├── publisher.py
│   └── consumer.py
│
├── models/
│
├── sensors/
│
├── requirements.txt
└── README.md
```

## Prerequisites

Install the following before running the project:

- Python 3
- Git (optional, for cloning the repository)
- Mosquitto MQTT Broker

Mosquitto must be installed separately because the project uses a local MQTT broker.

## Installation and Setup

### 1. Download the project

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_LINK
```

Alternatively, download the repository as a ZIP file from GitHub and extract it.

Open the project folder in VS Code or Command Prompt.

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

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

The publisher and consumer are configured to connect to:

- Broker: `localhost`
- Port: `1883`
- Topic: `factory/sensors`

## Running the Project

Open three separate terminals in the project folder. Activate the virtual environment in each terminal.

### Terminal 1: Start the MQTT Consumer

```bash
python messaging/consumer.py
```

The consumer receives sensor readings, stores them in the SQLite database, and detects anomalies.

It also automatically creates the database and required tables if they do not exist.

### Terminal 2: Start the Sensor Publisher

```bash
python messaging/publisher.py
```

The publisher generates sensor readings, injects simulated faults, and sends the data to the MQTT broker.

### Terminal 3: Start the Flask Dashboard

```bash
python dashboard/app.py
```

Open the following address in your browser:

http://127.0.0.1:5000

The dashboard displays the incoming sensor readings, detected anomalies, maintenance alerts, and historical data.

## Anomaly Detection

The system uses a rolling statistical approach based on Z-score analysis.

It compares incoming sensor readings with previous readings to identify unusual changes.

The configured Z-score threshold is 1.5.

Detected anomalies are classified into three severity levels:

| Severity | Absolute Z-score | Recommended Action |
|---|---|---|
| High | 5 or above | Immediate inspection |
| Medium | 3.5 to below 5 | Investigate the equipment |
| Low | Above 1.5 to below 3.5 | Continue monitoring |

A 30-second alert cooldown is applied separately for each sensor and severity level to reduce repeated alerts.

## Database

The system uses SQLite to store:

- Sensor readings
- Timestamps
- Anomaly scores
- Alert severity
- Maintenance recommendations

The database is created automatically when the MQTT consumer starts.

A fresh installation starts with an empty database. Previous readings and alerts are not included in the GitHub repository.

## Troubleshooting

**1. MQTT connection refused**

- Make sure Mosquitto is installed.
- Check that the MQTT broker is running.
- Verify that port `1883` is available.

**2. No sensor readings on the dashboard**

- Make sure the MQTT broker is running.
- Start the consumer before the publisher.
- Check that both use the same broker address and topic.

**3. Database or table not found**

- Start the MQTT consumer first.
- It creates the database and required tables automatically.
- Then start the Flask dashboard.

**4. Missing Python modules**

Run:

```bash
pip install -r requirements.txt
```

## Note

This project uses simulated sensor readings and injected faults for testing and demonstration. Anomaly alerts are early warning indicators and do not independently confirm equipment failure.

## Author

Developed as an IoT-based Predictive Maintenance project.