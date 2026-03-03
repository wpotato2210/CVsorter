# ColourSorter

[![CI](https://img.shields.io/badge/ci-placeholder-lightgrey)](#) [![PyPI](https://img.shields.io/badge/pypi-placeholder-lightgrey)](#) [![License](https://img.shields.io/badge/license-placeholder-lightgrey)](#)

Deterministic computer-vision bench tooling for lane-based sort decisioning, scheduling, and transport validation.

## Features

- Replay and live frame execution modes.
- Config-driven runtime behavior (`bench_runtime.yaml`).
- Multiple detection providers (`opencv_basic`, `opencv_calibrated`, `model_stub`).
- Scenario evaluation with pass/fail thresholds.
- Artifact generation (`summary.json`, `events.jsonl`, `telemetry.csv`, optional snapshots/report).
- Optional PySide6 bench GUI.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional extras:

```bash
python -m pip install -e .[serial]
python -m pip install -e .[dev]
```

## Quick start

GUI:

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

Scenario evaluator:

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

Replay bench run:

```bash
PYTHONPATH=src python -m coloursorter.bench.cli --mode replay --source data --artifact-root artifacts/bench --text-report
```

## CLI usage example

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 9 --peak-rtt-ms 15
```

## Documentation

- [Quick Start](QUICK_START.md)
- [User Manual](USER_MANUAL.md)
- [Developer Guide](DEVELOPER_GUIDE.md)

## Developer setup

```bash
python -m pip install -e .[dev]
pytest -q
```

Use installed entry points (`coloursorter-bench-gui`, `coloursorter-bench-cli`) to validate packaging/import behavior.

## License

License placeholder.
