# TESTING

## Framework and Commands
- Primary framework: `pytest` with optional `pytest-cov`.
- Project test command: `scripts/run_tests.bat` (repository standard `run_tests.bat` flow).
- Coverage command: `pytest --cov=src/coloursorter --cov-report=xml:coverage.xml`.

## Mocking Strategy (Hardware / I/O)
- Never call live cameras, serial ports, or MCU devices in unit tests.
- Use `pytest` monkeypatch or `unittest.mock` to replace:
  - frame sources (`LiveFrameSource`, replay/live adapters)
  - transports (`SerialMcuTransport`, `Esp32McuTransport`, low-level `send`/`send_command`)
  - filesystem writes and external CV helpers when needed.
- Keep mocks deterministic (fixed return values, no wall-clock dependencies where avoidable).

## Coverage Targets
- Target: 80%+ on critical modules.
- Critical modules for this batch:
  - `bench/runner.py`
  - `bench/cli.py`
  - `deploy/detection.py`
  - `deploy/pipeline.py`
  - `runtime/live_runner.py`
  - `train/*.py`
  - `infer/infer.py`
  - `ingest/*.py`

## Guidelines for Adding New Tests
- Place tests in `tests/` and use `test_*.py` naming.
- Prefer one module-focused test file per target area.
- Include normal-path, boundary, and error-path cases.
- Use fixtures/dummy payloads for repeated setup.
- Keep tests isolated, deterministic, and side-effect minimal.

## Safety Rules
- Preserve all existing tests exactly as-is.
- Do not modify production source during test-only tasks.
- Isolate generated tests so failures are attributable to new test logic.
- Avoid runtime package installs or network-coupled test behaviors.
