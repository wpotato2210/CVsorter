# ColourSorter Quick Start

**Version:** 0.1.0  
**Package:** `coloursorter`

## System requirements

- Python 3.12 (compatible with project requirement `>=3.10,<3.13`)
- Linux/macOS/Windows shell
- Optional: webcam for live mode
- Optional: serial device + `pyserial` for hardware transport mode

## Setup (step-by-step)

### 1) Open a terminal in the project folder

```bash
cd /path/to/ColourSorter
```

### 2) Create a virtual environment

```bash
python3.12 -m venv .venv
```

If that command fails because `python3.12` is unavailable, use:

```bash
python -m venv .venv
```

### 3) Activate the environment

- macOS/Linux:

  ```bash
  source .venv/bin/activate
  ```

- Windows PowerShell:

  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

After activation, your terminal prompt should start with `(.venv)`.

### 4) Install ColourSorter

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional extras:

```bash
python -m pip install -e .[serial]   # serial transport support
python -m pip install -e .[dev]      # test dependencies
```

### 5) Confirm install succeeded

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

You should see scenario output with pass/fail values.

`coloursorter-bench-cli` note: nominal/stress scenarios can pass with latency-only inputs, but fault/recovery checks require explicit `--safe-transitions` and `--recovered-from-safe` values.

Expected mixed output (latency-only inputs):

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

Expected all-pass output (fault/recovery inputs provided with compliant RTT values):

```bash
coloursorter-bench-cli --avg-rtt-ms 9 --peak-rtt-ms 15 --safe-transitions 1 --recovered-from-safe
```

## Run the app

Run these commands from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

GUI bench app:

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

Scenario CLI check:

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

Baseline replay pipeline run (run from repository root `/path/to/ColourSorter`):

```bash
PYTHONPATH=src python -m coloursorter.bench.cli \
  --mode replay \
  --source data \
  --runtime-config configs/bench_runtime.yaml \
  --lane-config configs/lane_geometry.yaml \
  --calibration configs/calibration.json \
  --max-cycles 50 \
  --artifact-root artifacts/bench \
  --text-report
```

## Minimal config example

```yaml
motion_mode: FOLLOW_BELT
homing_mode: SKIP_HOME
frame_source:
  mode: replay
  replay_path: data
  replay_frame_period_s: 0.033333333
transport:
  kind: mock
  max_queue_depth: 8
  base_round_trip_ms: 2.0
  per_item_penalty_ms: 0.8
```

## Expected output behavior

- CLI prints artifact directory and scenario pass/fail summary.
- Replay bench writes artifacts such as:
  - `summary.json`
  - `events.jsonl`
  - `telemetry.csv`
  - `config_snapshot.json` (when config snapshot is provided)
  - `report.txt` (with `--text-report`)

## Basic testing workflow (for first-time testers)

Run all testing commands from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

1. Make sure `(.venv)` is visible in your prompt.
2. Install test dependencies:

   ```bash
   python -m pip install -e .[dev]
   ```

3. Run all tests:

   ```bash
   pytest -q
   ```

4. Run one focused file when iterating quickly:

   ```bash
   pytest -q tests/test_bench_controller.py
   ```

5. If a test fails, read the first traceback block in terminal output. It usually shows:
   - which file/test failed,
   - expected vs actual value,
   - line number to inspect.
