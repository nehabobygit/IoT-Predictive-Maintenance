# Dataset Attribution and Licensing

## AI4I 2020 Predictive Maintenance Dataset

Sven Matzka, AI4I 2020 Predictive Maintenance Dataset, UCI Machine Learning Repository, DOI `10.24432/C5HS5C`. UCI identifies the data as synthetic and licenses it under CC BY 4.0. `data/ai4i2020.csv` supplies concurrent machine-failure labels for the original and improved classifiers. Product IDs and failure-mode labels are excluded from model inputs. The miss audit uses mode labels only after scoring. [UCI dataset and licensing](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)

## Skoltech Anomaly Benchmark

SKAB's recorded test-rig data, notebooks and upstream code are vendored under `data/SKAB-master/` with the upstream GPL-3.0 license. The dashboard and MQTT integration live outside that upstream tree. The project's exported `results/skab_grouped_fixture.csv.gz` is a subset and transformation of the upstream data. It preserves timestamps, anomaly and change-point labels, and identified measurement channels. The corresponding JSON report includes source file hashes. The Docker build excludes the upstream tree, so replay requires mounting or copying the recordings into the configured data directory. [SKAB source and license](https://github.com/waico/SKAB)

Keep upstream notices and the license with redistributed SKAB materials. GPL-3.0 specifies obligations for conveying covered materials, including source-availability and notice provisions where they apply. Review the exact contents and terms of any commercial redistribution. This project does not certify that a particular package or commercial deployment is cleared. [Bundled GPL-3.0 text](data/SKAB-master/LICENSE)

## Simulated sensor telemetry and NAB

The project's simulator generates artificial five-sensor readings and fault labels. It supplies the simulator anomaly benchmark and the separate six-sample forecast. Humidity in SKAB replay is simulated because the recorded SKAB stream does not provide that sensor. Acceleration retains `g` in recorded SKAB, and the separate simulated vibration stream uses `mm/s`.

Numenta Anomaly Benchmark (NAB) is an optional upstream research dataset used by archived experiments. Current acceptance metrics exclude it. Consult and retain the source project's applicable notices if redistributing its materials. [NAB source](https://github.com/numenta/NAB)
