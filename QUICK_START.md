# ColourSorter Quick Start

**Version:** 0.1.0  
**Package:** `coloursorter`

## System requirements

- Python 3.12 (compatible with project requirement `>=3.10,<3.13`)
- Linux/macOS/Windows shell
- Optional: webcam for live mode
- Optional: serial device + `pyserial` for hardware transport mode

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional extras:

```bash
python -m pip install -e .[serial]   # serial transport support
python -m pip install -e .[dev]      # test/lint dependencies
```

## Run the app

GUI bench app:

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

Scenario CLI check:

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

Baseline replay pipeline run:

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
