# ColourSorter

[![CI](https://github.com/ColourSorter/ColourSorter/actions/workflows/ci.yml/badge.svg)](https://github.com/ColourSorter/ColourSorter/actions/workflows/ci.yml) [![Package](https://img.shields.io/pypi/v/coloursorter?label=package)](https://pypi.org/project/coloursorter/) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Deterministic computer-vision bench tooling for lane-based sort decisioning, scheduling, and transport validation.

## Features

- Replay and live frame execution modes.
- Config-driven runtime behavior (`bench_runtime.yaml`).
- Multiple detection providers (`opencv_basic`, `opencv_calibrated`, `model_stub`).
- Scenario evaluation with pass/fail thresholds.
- Artifact generation (`summary.json`, `events.jsonl`, `telemetry.csv`, optional snapshots/report).
- Optional PySide6 bench GUI.

## Fast path (new developer)

Run from repository root:

```bash
./setup.sh && ./run.sh
```

Container alternative:

```bash
docker build -t app . && docker run --rm app
```

Detailed steps: [INSTALL.md](INSTALL.md).

## Installation (beginner friendly)

If you have never used terminal commands before, follow these steps exactly.

### 1) Open a terminal

- **Windows**: open **PowerShell**.
- **macOS**: open **Terminal**.
- **Linux**: open your usual terminal app.

### 2) Go to the project folder

Replace `/path/to/ColourSorter` with your local folder path.

```bash
cd /path/to/ColourSorter
```

Use `pwd` (macOS/Linux) or `Get-Location` (PowerShell) to confirm you are in the right folder.

### 3) Create a virtual environment

This creates an isolated Python environment so project packages do not conflict with global packages.

```bash
python3.12 -m venv .venv
```

If `python3.12` is not found, try `python -m venv .venv`.

### 4) Activate the virtual environment

- **macOS/Linux (bash/zsh):**

  ```bash
  source .venv/bin/activate
  ```

- **Windows PowerShell:**

  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

- **Windows Command Prompt (cmd.exe):**

  ```bat
  .\.venv\Scripts\activate.bat
  ```

You should see `(.venv)` at the start of your prompt after activation.

### 5) Install dependencies

Run these commands from the repository root (for example `C:\Users\<you>\Documents\CVsorter-main`), not from `.venv\Scripts`.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional installs:

```bash
python -m pip install -e .[serial]  # serial transport support
python -m pip install -e .[dev]     # test dependencies (pytest, tooling)
```

### 6) Quick verification after install

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

If this runs and prints a scenario summary, installation is working.

## Quick start

Run these commands from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

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

Run this command from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 9 --peak-rtt-ms 15
```

## Documentation

- [Quick Start](QUICK_START.md)
- [User Manual](USER_MANUAL.md)
- [Developer Guide](DEVELOPER_GUIDE.md)

## Testing (beginner friendly)

Run all testing commands below from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

### What testing means here

Tests automatically check that core behaviour still works after changes.
The test runner used by this project is `pytest`.

### 1) Install test dependencies

```bash
python -m pip install -e .[dev]
```

### 2) Run the full test suite

```bash
pytest -q
```

### 3) Run one test file (faster when debugging)

```bash
pytest -q tests/test_preprocess.py
```

### 4) Run one specific test case

```bash
pytest -q tests/test_preprocess.py -k lane
```

### 5) Understand the result

- `passed`: the check succeeded.
- `failed`: behaviour changed unexpectedly; inspect the traceback in terminal output.
- `error`: test setup/import failed (often missing dependency or wrong environment).

If commands such as `pytest` are not found, ensure your virtual environment is activated (prompt starts with `(.venv)`).

Use installed entry points (`coloursorter-bench-gui`, `coloursorter-bench-cli`) to validate packaging/import behavior.

## License

This project is licensed under the [MIT License](LICENSE).
