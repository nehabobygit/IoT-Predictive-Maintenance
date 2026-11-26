# Final Consolidated Project Completion Report

Execution date 26 November 2026. The current Docker project is `iot-maintenance-final`. Its dashboard is at http://localhost:5002 and its MQTT host listener is `127.0.0.1:8885`. All four services were healthy after acceptance. Use **Create an account** on first visit. The temporary verification accounts were removed. Existing native services and prior Compose stacks remain independent.

## 1. Initial project condition

The working tree at Git base `de719f3` already contained a functioning SQLite, Flask, Mosquitto and Paho MQTT pipeline with three simulated machines, a hybrid detector, a validated simulator forecast, a default improved AI4I forest, source-aware replays, and existing dashboard, alert and maintenance pages. Gaps included one shared dashboard identity, no link between a new task and its alert, limited maintenance provenance, no readiness checks or durable broker state, a backup loop without independent restore verification, and a weak SKAB evaluation protocol.

## 2. Combined review tracker

[CONSOLIDATED_REVIEW_COMPLETION_TRACKER.md](CONSOLIDATED_REVIEW_COMPLETION_TRACKER.md) maps the findings transcribed in the directive and classifies the current result for each requirement. The standalone 20 November First Reference Verification and 25 November Second Technical Evaluation reports were unavailable in the materials checked. Findings absent from the provided excerpts remain unavailable for literal reconciliation. [The earlier project audit](PROJECT_AUDIT.md) preserves the prior execution evidence.

## 3. Existing features retained

Kept the existing visual design, SQLite schema entities, asset and run metadata, five-sensor simulator, TLS certificate validation, role ACLs, two MQTT topics, UUID event deduplication, alert severity and cooldown, maintenance pages, Python/NumPy models and Docker topology. The simulator forecast retains its six-sample horizon. Re-tested the existing 29 tests in the expanded suite, and re-scored the saved AI4I models on the documented split.

## 4. Improvements made

- Added a source-bound asset registry with equipment names and types and optional controlled registrations. Authenticated asset and monitoring APIs expose that metadata.
- Added a validation-selected, cross-sensor degradation rule using corroborating changes in vibration, temperature, pressure and current. Retained the earlier hybrid and rolling detector as benchmark comparisons.
- Added group-held-out SKAB evaluation, per-sequence metrics, causal warmup, actual-duration delay and false alarm calculations, source hashes and a compressed labeled fixture.
- Added individual dashboard admin, operator and viewer identities, hash-based passwords, login throttling, CSRF on state-changing maintenance and authentication forms, and an optional HTTPS configuration with secure cookies.
- Linked new maintenance tasks to their originating alert. Assignment and priority changes, acknowledgements, task creation and completion are transactionally recorded with the logged-in actor, timestamps and before/after details. Legacy tasks remain readable.
- Unified MQTT connection settings. Added broker persistence, a stable subscriber ID, application ACK after processing, reconnection, and broker, subscriber, publisher and dashboard database readiness probes.
- Scoped model files to the local models directory and checked the exact bytes before deserialization. Added a one-shot backup command and an integrity-checked restore that reserves a new path and refuses existing destinations.
- Added benchmark documentation, provenance and redistribution notes, and added the expanded native/Linux test suite to the existing CI configuration.

## 5. Machine learning evaluations

Counts are given as TP / FP / FN / TN. Simulator, SKAB and AI4I have independent labels and test sets.

| Simulator anomaly detector, same 6,000 test readings | Accuracy | Precision | Recall | F1 | TP / FP / FN / TN |
|---|---:|---:|---:|---:|---:|
| Rolling Z-score | 63.65% | 55.41% | 96.20% | 70.31% | 2,583 / 2,079 / 102 / 1,236 |
| Prior hybrid | 74.93% | 88.17% | 50.80% | 64.46% | 1,364 / 183 / 1,321 / 3,132 |
| Hybrid with cross-sensor trend rule | 82.12% | 90.75% | 66.85% | 76.99% | 1,795 / 183 / 890 / 3,132 |

Selection used seeds 500-514 and a validation precision floor four percentage points below the prior hybrid. The scale of 0.75 was frozen for final seeds 600-619. The new detector recovered 431 additional labeled points at the same false-positive count. All 534 labeled simulator episodes had a detection. Median detection delay was 0 s, and 90 grouped false alarms over 3.3 simulated hours extrapolate to about 218 per eight hours. This extrapolation reflects accelerated injected simulator behavior. The historical 418-reading results are a different run. [Simulator evidence](results/simulator_grouped_metrics.json)

| SKAB recorded test rig, 18,161 final readings | Accuracy | Precision | Recall | F1 | TP / FP / FN / TN |
|---|---:|---:|---:|---:|---:|
| Rolling Z-score | 48.74% | 37.98% | 59.68% | 46.42% | 4,033 / 6,585 / 2,725 / 4,818 |
| Validation-selected robust reference | 55.34% | 43.86% | 71.46% | 54.36% | 4,829 / 6,181 / 1,929 / 5,222 |

`valve1` was used for parameter selection. The `valve2` and `other` groups supply 18 final sequences. Their first 60 observations were used only for the causal reference and excluded from scoring. Prior exploratory project scripts had inspected the final groups. The protocol establishes independence within this evaluation. New external recordings are needed for an untouched test. The reference detected 17 of 18 labeled episodes with 0 s median detection delay for detected episodes. It still had a 54.21% point false-positive rate and about 1,839 grouped false alarms per eight hours extrapolated from 5.4675 observed hours. The result supports a research comparison, and the online SKAB replay still uses its existing rolling detector. [Sequence results](results/skab_grouped_metrics.json) · [Labeled fixture](results/skab_grouped_fixture.csv.gz)

| AI4I held-out concurrent classification | Accuracy | Precision | Recall | F1 | ROC AUC | PR AUC | False-negative rate | TP / FP / FN / TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Always normal | 96.60% | 0% | 0% | 0% | 50.00% | 3.40% | 100.00% | 0 / 0 / 51 / 1,450 |
| Original forest | 97.80% | 70.45% | 60.78% | 65.26% | 96.54% | 69.77% | 39.22% | 31 / 13 / 20 / 1,437 |
| Improved retained forest | 99.20% | 100.00% | 76.47% | 86.67% | 97.08% | 87.76% | 23.53% | 39 / 0 / 12 / 1,450 |

Both AI4I models used the same stratified holdout. Model selection and threshold tuning used validation only. The earlier decision-tree and weighted/unweighted forest comparison remains reproducible. The improved forest recovered nine of the original missed records and missed one record the original detected. The original 20 misses included nine tool-wear, five power, four overstrain and two with no listed mode flags. The revised 12 misses are nine tool-wear, one power and two unflagged. According to the UCI generator description, some tool-wear failures are randomly assigned among wear-triggered events. The independent UDI-ordered experiment reached 74.07% F1. [AI4I miss audit](results/ai4i_miss_audit.json) · [Source dataset](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)

The separate six-sample live simulator forecast achieved 99.20% accuracy, 94.66% precision, 91.85% recall and 93.23% F1 on independent simulator seeds. This forecast has its own compatible inputs. AI4I labels concurrent outcomes. Neither benchmark establishes remaining useful life or a real-world forecast horizon. [Live forecast results](results/live_maintenance_metrics.json)

## 6. Asset and maintenance verification

Three simultaneous simulator streams advanced in Chrome. In the stored backup, each simulator asset had 214 readings. The SKAB replay added 40 records with 40 source timestamps and 40 simulated-humidity flags, with acceleration in `g`. AI4I replay produced distinct 100-record and three-record runs. The latest replay was the three-record run.

An injected 75 deg C reading raised high-severity overheating alert 28 for `SIM-MOTOR-001`. Chrome scheduled task 1 from that alert using its cooling-system recommendation. The administrator acknowledged the alert, assigned Engineer A at medium priority, changed to Engineer B at high priority, and completed the task. The original actor and all four transitions were retained. The viewer could read the result and received HTTP 403 on a write.

## 7. Security and deployment

The isolated final Compose project passed `up --build --wait`. Broker, consumer, publisher and dashboard reached healthy states. Broker TLS authenticated both roles. Actual network probes rejected anonymous MQTT and a mismatched certificate hostname. Chrome verified first-account registration, login and role restrictions. The regression suite exercised failed-login throttling and CSRF rejection. A separate HTTPS run returned HTTP 200 using the trusted local certificate and `Secure`, `HttpOnly` and `SameSite=Lax` session flags. Docker ports bind to loopback and Flask debug mode is disabled. The system provides operator decision support without an actuation path.

## 8. Backup and broker recovery

Six distinct controlled QoS 1 messages were acknowledged by the broker with the consumer stopped. One duplicate and three invalid messages were also sent. After restarting the broker and resuming the subscriber, SQLite contained each valid ID exactly once, with no invalid rows. The same publisher run resumed. Additional live readings and both replay types were persisted after recovery.

An online SQLite snapshot was restored to a separately named file. `PRAGMA integrity_check` returned `ok`, and the restored record counts matched the backup. The restored database contained 682 readings, 105 alerts, 294 anomaly events, 609 live forecasts, 103 replay predictions, one linked completed task, one acknowledgement and four audit rows. The test preserved the task-to-alert and machine relationships. A separate regression produced eight snapshots and verified seven-copy retention.

## 9. Automated tests

| Environment | Executed | Passed | Failed |
|---|---:|---:|---:|
| Windows Python 3.12 virtual environment | 32 | 32 | 0 |
| Final Docker Linux ARM64 image | 32 | 32 | 0 |

The tests include maintenance role and CSRF checks, login throttling, malformed MQTT handling, invalid model hashes and paths, safe backup retention and restore, and the previous sensor, anomaly, classifier and dashboard tests. Hosted CI was updated and was not triggered by this local run.

## 10. Acceptance demonstrations

| Demonstration | Result | Evidence |
|---|---|---|
| Clean setup | PASSED | Isolated Compose database and broker volume, healthy services, Chrome account creation and login |
| Multiple sensor streams | PASSED | Three live asset streams, preserved recorded units, wrong-unit and unknown-asset rejection, duplicate suppressed |
| Anomaly and maintenance | PASSED | Controlled alert 28 and task 1, assigned and completed with four authenticated audit entries |
| ML results | PASSED | Three independent report sections rendered in Chrome and separately produced JSON reports |
| Backup and recovery | PASSED | Six queued events recovered, publisher continued, verified backup restored with full relationships |
| Security | PASSED | TLS and anonymous rejection, viewer 403, login throttling and CSRF tests, HTTPS cookie verification |

Workstation evidence is under `%TEMP%\iot-maintenance-final-review`. Files include `recovery-evidence.json`, `browser-evidence.json`, `backup-restore-evidence.json`, `dashboard-https.json`, `linux-tests.txt`, and the Chrome captures `final-live-sensors.png`, `final-maintenance.png` and `final-model-evaluation.png`.

## 11. Remaining limitations

- The stand-alone review reports were unavailable. Exact findings beyond the quoted material could not be reconciled.
- SKAB's existing recordings were previously explored, generalization to untouched field data is unverified, and its false-alert burden is high. AI4I recall and simulator anomaly F1 remain below the aspirational target.
- Persistent QoS 1 was tested through a graceful broker restart. Publisher-process or host loss can discard messages held only in memory. Extended hardware deployment, physical maintenance outcomes and remaining useful life were outside this demonstration.
- Legacy maintenance tasks without originating alert information retain their original unlinked history. Creating or assigning an operator identity does not establish that physical work occurred.

## 12. Exact startup and reproduction

From the repository root, provision a certificate for broker hostname `mqtt`, and include localhost in the certificate SAN for host replay. Prepare `server.crt`, `server.key`, `project_passwords.txt`, and `project_acl.txt` in `docker_mqtt_security/` or set `MQTT_SECURITY_DIR`. Match `MQTT_PUBLISHER_PASSWORD` and `MQTT_CONSUMER_PASSWORD` in your local `.env` to those Mosquitto hashes. The certificate, ACL and password-file creation steps are in [README.md](README.md).

```powershell
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 140
docker compose ps
docker compose exec publisher python -m messaging.ai4i_replay_publisher --limit 100
docker compose exec publisher python -m sensors.skab_replay --limit 40
docker compose exec dashboard python -m detection.auto_backup --once
```

The default dashboard address is http://localhost:5000. With an alternate data mount, copy the AI4I CSV and SKAB `valve1` recordings into that mount. The dashboard and consumer initialize the SQLite schema on startup.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector detection.test_live_system detection.test_review_workflow -q
.\venv\Scripts\python.exe -m detection.audit_ai4i_misses
.\venv\Scripts\python.exe -m detection.evaluate_simulator_grouped
.\venv\Scripts\python.exe -m detection.evaluate_skab_grouped
```

For the already-running isolated verification project, select its existing runtime directories and ports.

```powershell
$review = Join-Path $env:TEMP 'iot-maintenance-final-review'
$env:IOT_DATA_DIR = Join-Path $review 'data'
$env:MQTT_SECURITY_DIR = Join-Path $env:TEMP 'iot-compose-verification/security'
$env:DASHBOARD_HOST_PORT = '5002'
$env:MQTT_HOST_PORT = '8885'
docker compose -p iot-maintenance-final ps
docker compose -p iot-maintenance-final up -d --build --wait --wait-timeout 140
```
