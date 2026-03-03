# ColourSorter User Manual

## 1. Title Page

**Product:** ColourSorter  
**Version:** 0.1.0  
**Audience:** Operators and validation users running bench simulations and telemetry checks.

## 2. Overview

ColourSorter provides a deterministic bench pipeline for object detection decisions, lane assignment, scheduling, and transport simulation. It supports:

- Replay-mode execution from files.
- Live-mode frame capture.
- Built-in scenario evaluation thresholds.
- Artifact generation for verification and reporting.
- Optional GUI monitoring for bench state and logs.

## 3. System Requirements

- Python 3.12 recommended (project supports `>=3.10,<3.13`).
- `pip` and virtual environments.
- OpenCV runtime dependencies.
- For GUI: PySide6-compatible desktop environment.
- For serial transport mode: compatible serial hardware and optional `pyserial` extra.

## 4. Installation

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

## 5. Getting Started

### Run quick scenario checks

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

### Run GUI bench app

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

### Run replay pipeline and write artifacts

```bash
PYTHONPATH=src python -m coloursorter.bench.cli \
  --mode replay \
  --source data \
  --max-cycles 100 \
  --artifact-root artifacts/bench \
  --runtime-config configs/bench_runtime.yaml \
  --lane-config configs/lane_geometry.yaml \
  --calibration configs/calibration.json \
  --text-report
```

## 6. Detailed Feature Guide

### Replay frame processing
- Reads replay frames from a directory, video, or image path.
- Converts each frame to RGB for downstream processing.
- Runs configured detection provider on each frame.

### Detection provider selection
- `opencv_basic`
- `opencv_calibrated`
- `model_stub`

Provider can come from runtime config and be overridden at CLI runtime.

### Decision and scheduling
- Lane assignment is computed from `lane_boundaries_px`.
- Rejection reason is derived from rule thresholds.
- Valid lane+trigger values are converted to scheduled commands.

### Transport simulation/hardware path
- Mock transport for deterministic bench testing.
- Serial transport option for hardware integration mode.

### Artifact production
- Structured summary, events, telemetry CSV, and optional text report.
- Optional frame snapshots when enabled.

## 7. CLI Reference

### `coloursorter-bench-cli`

Scenario threshold evaluator.

```bash
coloursorter-bench-cli --avg-rtt-ms <float> --peak-rtt-ms <float> [options]
```

Common options:

- `--scenario` evaluate one scenario name; default evaluates all.
- `--safe-transitions` safe mode transition count.
- `--watchdog-transitions` watchdog transition count.
- `--recovered-from-safe` flag indicating recovery.

### `python -m coloursorter.bench.cli`

Main bench execution CLI.

Key options:

- `--mode replay|live`
- `--source <path>`
- `--camera-index <int>`
- `--frame-period-s <float>`
- `--max-cycles <int>`
- `--scenario <name>` (repeatable)
- `--artifact-root <path>`
- `--text-report`
- `--lane-config <path>`
- `--calibration <path>`
- `--runtime-config <path>`
- `--enable-snapshots`
- `--detector-provider <name>`
- `--detector-threshold <float>`
- `--calibration-mode fixed|adaptive`

## 8. Configuration Reference

### `configs/bench_runtime.yaml`
Primary startup config:

- `motion_mode`, `homing_mode`
- `frame_source` (mode, replay path, period)
- `camera` (index, period)
- `transport` (kind, queue depth, RTT settings, serial subkeys)
- `cycle_timing` (period and queue policy)
- `scenario_thresholds` (nominal/stress/fault pass bounds)
- `detection` provider-specific settings
- `baseline_run` defaults

### `configs/lane_geometry.yaml`
- Fixed `lane_count` (22 expected)
- `lane_boundaries_px`
- `mm_per_pixel`
- `camera_to_reject_mm`

### `configs/calibration.json`
- `mm_per_pixel`
- `calibration_hash`

## 9. GUI Usage Guide

Start:

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

The GUI displays:
- Frame preview.
- Lane/queue state.
- Scheduler/controller status labels.
- SAFE/WATCHDOG indicators.
- Log table entries with timestamp, lane decision, rejection reason, RTT, and ACK code.

## 10. Step-by-Step Examples

### Example A: basic scenario threshold check

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 9 --peak-rtt-ms 15
```

Expected: `[PASS] nominal: ...` and exit code `0`.

### Example B: replay run with report

```bash
PYTHONPATH=src python -m coloursorter.bench.cli \
  --mode replay \
  --source data \
  --artifact-root artifacts/session_001 \
  --text-report
```

Expected: `artifact_dir=...`, `overall=PASS|FAIL`, scenario lines.

## 11. Troubleshooting

- **Unknown scenario error**: use valid built-in scenario names.
- **Config validation failure**: verify enum values and numeric ranges in runtime config.
- **Calibration load errors**: validate hash and JSON schema fields.
- **No frames in replay mode**: confirm `--source` path contains readable media.
- **GUI launch issues**: check PySide6 install and desktop runtime support.

## 12. FAQ

**Q: Can I run only one scenario?**  
A: Yes, pass `--scenario <name>`.

**Q: Does the project support live camera input?**  
A: Yes, use `--mode live` and camera parameters.

**Q: Are artifacts always written?**  
A: Yes for bench execution, to `--artifact-root`.

**Q: How do I test serial mode dependencies?**  
A: Install `.[serial]` and set transport kind/config accordingly.

## 13. Glossary

- **Bench**: deterministic validation environment for pipeline and transport behavior.
- **Detection provider**: component that returns object detections for each frame.
- **Decision payload**: classified object result with lane/reason metadata.
- **Scheduled command**: lane + trigger position instruction sent to transport.
- **RTT**: round-trip transport latency metric.
