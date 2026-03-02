# ColourSorter

Colour sorter project beginning with ChatGPT generated OpenSpec.

## Installation

```bash
python -m pip install -e .
```

For test/lint tooling:

```bash
python -m pip install -e .[dev]
```

## Launch commands

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

```bash
coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20
```

## Bench bring-up

1. Install project dependencies: `python -m pip install -e .`.
2. Validate bench scenarios quickly: `coloursorter-bench-cli --avg-rtt-ms 10 --peak-rtt-ms 20`.
3. Start the GUI bench app with canonical runtime config: `coloursorter-bench-gui --config configs/bench_runtime.yaml`.

## Runtime configuration

- Canonical bench startup config: `configs/bench_runtime.yaml`.
- Migration notes from legacy startup keys: `docs/bench_runtime_config_migration.md`.
- Enum migration notes: `docs/config_migration_v4.md`.

## Release done definition

A release is only considered finished after the hardware readiness gate passes.

1. Ensure required evidence is checked into `docs/artifacts/hardware_readiness/` per `docs/hardware_readiness_gate.md`.
2. Run `python tools/hardware_readiness_report.py --strict`.
3. Declare release complete only when the report returns `Overall status: PASS`.

## Baseline bean-sorting run (logged artifacts)

Run the baseline pipeline in replay mode with explicit run metadata:

```bash
PYTHONPATH=src python -m coloursorter.bench.cli \
  --mode replay \
  --source data \
  --max-cycles 100 \
  --run-id baseline-001 \
  --test-batch-id batch-a \
  --artifact-root artifacts/baseline \
  --enable-snapshots \
  --detector-provider opencv_basic \
  --detector-threshold 0.5 \
  --calibration-mode fixed \
  --text-report
```

Artifacts generated per run include:
- `summary.json`
- `events.jsonl`
- `telemetry.csv`
- `config_snapshot.json`
- `frames/` (if `--enable-snapshots`)

### Threshold tuning and retraining

- Start with conservative reject threshold (`--detector-threshold` near `0.5` or higher).
- Inspect confidence distribution in `events.jsonl` before adjusting thresholds.
- Tune one variable at a time: threshold, provider mapping, calibration mode.
- For retraining preparation, use deterministic augmentation in `coloursorter.train.augment_dataset(...)` and record train artifact metadata with `coloursorter.train.run_baseline_training(...)`.
