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
