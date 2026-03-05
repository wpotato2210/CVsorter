# Install and Run

## Local one-command setup

From the repository root:

```bash
./setup.sh && ./run.sh
```

What this does:

1. Creates a virtual environment at `.venv`.
2. Installs the project in editable mode.
3. Runs a deterministic smoke execution (`nominal` scenario).

## Docker

From the repository root:

```bash
docker build -t app .
docker run --rm app
```

The container runs:

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 9 --peak-rtt-ms 15
```

## Smoke test

After local setup:

```bash
scripts/smoke_test.sh
```

This validates:

- critical imports (`cv2`, `numpy`)
- bench CLI execution path
