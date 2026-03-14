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

### Windows `cmd.exe` troubleshooting (common pitfalls)

If you see errors like `'..\\..' is not recognized` or `'.' is not recognized as an internal or external command`, `cmd.exe` is treating text as commands.

- Use `cd ..\\..` to move folders. Do **not** run `..\\..` by itself.
- Run test commands from the repo root, not from `.venv\\Scripts`.
- Do not paste pytest output (dots, coverage table rows) back into the terminal. Those lines are output, not commands.
- Prefer module-invoked commands to avoid PATH ambiguity:

  ```bat
  python -m pytest tests
  python -m pytest --cov=src/coloursorter --cov-report=term --cov-report=xml
  ```

If you get `AttributeError: module 'logging' has no attribute 'getLogger'`, check for a local file named `logging.py` in your current working directory and rename/remove it; it can shadow Python's standard `logging` module.

### 5) Install dependencies (canonical method)

Run these commands from the repository root (for example `C:\Users\<you>\Documents\CVsorter-main`), not from `.venv\Scripts`.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

`pyproject.toml` is the source of truth for runtime/dev/optional dependencies. `requirements.txt` is auto-generated from `pyproject.toml` for compatibility workflows.

Optional installs:

```bash
python -m pip install -e .[serial]  # serial transport support
python -m pip install -e .[dev]     # test dependencies (pytest, tooling)
```

Dependency sync guard (used in CI):

```bash
python scripts/sync_requirements.py --check
```

Regenerate `requirements.txt` after dependency edits:

```bash
python scripts/sync_requirements.py
```

### 6) Quick verification after install

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 10 --peak-rtt-ms 20
```

If this prints `[PASS] nominal`, installation is working.

## Quick start

Run these commands from the repository root (`/path/to/ColourSorter`) with your virtual environment activated.

GUI:

```bash
coloursorter-bench-gui --config configs/bench_runtime.yaml
```

Scenario evaluator:

```bash
coloursorter-bench-cli --scenario nominal --avg-rtt-ms 10 --peak-rtt-ms 20
```

Replay bench run (Linux/macOS):

```bash
PYTHONPATH=src python -m coloursorter.bench.cli --mode replay --source data --artifact-root artifacts/bench --text-report
```

Replay bench run (Windows Command Prompt):

```bat
set PYTHONPATH=src && python -m coloursorter.bench.cli --mode replay --source data --artifact-root artifacts/bench --text-report
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

### Wire Format

Deterministic line protocol rules for parser fixtures:

- ASCII only.
- Tokens are uppercase.
- Token separator is a single ASCII space (`0x20`).
- Line ending is exactly `\n`.
- No trailing spaces.

Versioned response rules:

| Version | Allowed responses | Payload policy |
| --- | --- | --- |
| v1 | `OK`, `ERR` | No payloads permitted. |
| v2 | `ACK_OK`, `ACK_BUSY`, `ERR_RANGE`, `ERR_TYPE`, `ERR_MODE`, `ERR_QUEUE`, `ERR_FRAME`, `ERR_UNKNOWN` | `ACK_*` must not include payloads. `ERR_*` may include one payload token only when the response definition requires detail text. |

`CAPS?` response normalization (v2):

- Fixed key order: `VER`, `RESP`, `PAYLOAD`.
- Exact response form: `CAPS VER=v2 RESP=<comma-separated response tokens> PAYLOAD=ERR_*:DETAIL`.
- No extra keys, no key reordering, no lowercase.

Canonical parser-fixture examples:

```text
OK\n
ACK_BUSY\n
CAPS VER=v2 RESP=ACK_OK,ACK_BUSY,ERR_RANGE,ERR_TYPE,ERR_MODE,ERR_QUEUE,ERR_FRAME,ERR_UNKNOWN PAYLOAD=ERR_*:DETAIL\n
```

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

### 2a) Phase 3 exit check (required): generate and verify `coverage.xml`

```bash
python -m pytest tests -q --cov=src/coloursorter --cov-report=xml
test -f coverage.xml
```

This Phase 3 gate is required for local verification and CI parity.

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
