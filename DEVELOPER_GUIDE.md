# ColourSorter Developer Guide

## 1. Architecture Overview

ColourSorter is organized as a deterministic CV bench stack:

1. Frame source (replay/live)
2. Detection provider
3. Pipeline runner
4. Rules-based decisioning
5. Scheduler command construction
6. Transport send/ack
7. Evaluation and artifact writing

The top-level package exposes pipeline primitives and separate bench/GUI entry points.

## 2. Package Structure Breakdown

- `src/coloursorter/preprocess`: lane geometry parsing and lane lookup.
- `src/coloursorter/calibration`: calibration model loading and integrity checks.
- `src/coloursorter/model`: core dataclasses for frames, detections, decisions.
- `src/coloursorter/eval`: rejection reason policy.
- `src/coloursorter/scheduler`: scheduled command contracts.
- `src/coloursorter/serial_interface`: transport framing and packet encoding.
- `src/coloursorter/deploy`: detection providers + pipeline orchestration.
- `src/coloursorter/bench`: frame sources, transport adapters, runner, scenarios, evaluation.
- `src/coloursorter/config`: enum constants and runtime config parsing/validation.
- `gui/bench_app`: PySide6 bench UI and controller integration.

## 3. Application Flow

- `coloursorter.bench.cli:main` parses args and loads runtime config.
- Scenario set is resolved from defaults or config thresholds.
- `PipelineRunner` is instantiated with lane + calibration paths.
- `BenchRunner.run_cycle` executes the per-frame processing cycle.
- Logs are evaluated and serialized via `bench.evaluation.write_artifacts`.

## 4. Core Modules and Responsibilities

- `deploy/pipeline.py`
  - Computes decisions from detections and geometry/calibration.
  - Builds scheduled commands for reject decisions.
- `deploy/detection.py`
  - Provider factory (`build_detection_provider`).
  - OpenCV-based and stub detection implementations.
- `bench/runner.py`
  - Tracks cycle timing, invokes pipeline, emits bench logs.
- `bench/evaluation.py`
  - Scenario pass/fail evaluation and artifact persistence.
- `config/runtime.py`
  - Runtime config model + schema/range validation.

## 5. Public APIs

High-level exports are re-exported in package `__init__` modules, including:

- `coloursorter.PipelineRunner`, `coloursorter.PipelineResult`
- Bench abstractions (`BenchRunner`, frame sources, scenarios, transports)
- Config model and validation types (`RuntimeConfig`, `ConfigValidationError`)

Console scripts in `pyproject.toml`:

- `coloursorter-bench-gui = gui.bench_app.app:main`
- `coloursorter-bench-cli = coloursorter.bench.scenario_runner:run`

## 6. Internal Data Flow

- Frame source emits `BenchFrame` / image payload.
- Detection provider emits `ObjectDetection` list.
- Pipeline emits `DecisionPayload` and `ScheduledCommand` values.
- Transport returns queue state and ACK/NACK semantics.
- Runner emits `BenchLogEntry` rows consumed by evaluator and GUI.

## 7. Configuration System

`RuntimeConfig` is loaded from YAML-like startup text using strict key/shape/range checks.

Validation highlights:
- enum validation for motion/homing and provider names
- numeric bounds for timing, thresholds, queue depth
- serial dependency checks when serial transport kind is selected

Related config assets:
- `configs/bench_runtime.yaml`
- `configs/lane_geometry.yaml`
- `configs/calibration.json`

## 8. Extension Points

- Add a detection provider in `deploy/detection.py` and wire into `build_detection_provider`.
- Add bench scenarios in `bench/scenarios.py`.
- Add transport implementation by extending `bench.transport.McuTransport`.
- Add additional artifact outputs in `bench/evaluation.py`.

## 9. Dependency Overview

Core runtime:
- `PySide6`
- `PySide6-Addons`
- `PyYAML`
- `opencv-python`

Optional:
- `pyserial` via `.[serial]`
- test/lint via `.[test]`, `.[lint]`, or `.[dev]`

## 10. Packaging & Editable Install Notes

Build system uses setuptools/wheel with `setuptools.build_meta`.

Editable install:

```bash
python -m pip install -e .
```

Packages are discovered from `src` and repository root for both `coloursorter*` and `gui*` namespaces.

Use entry points instead of direct module execution to keep import behavior aligned with installed package runtime.

## 11. CI / Testing

Pytest config:
- `testpaths = ["tests"]`
- `pythonpath = ["src"]`

Typical local command:

```bash
pytest -q
```

Ruff lint configuration is defined in `pyproject.toml` with `E/F/I/B` rule families.

## 12. Design Constraints

- Deterministic behavior is prioritized for bench reproducibility.
- Runtime namespace and CLI naming remain `coloursorter` for compatibility.
- Lane geometry currently assumes fixed 22-lane configuration at load time.
- Rejection decisions and scheduling enforce explicit threshold/range guards.
