# High-Value Repository Audit (Top 5)

## 1) CI matrix includes unsupported Python version
- **Severity:** Critical
- **Location:** `.github/workflows/ci.yml`
- **Evidence:** CI runs Python `3.9` while package metadata requires `>=3.10,<3.13`.
- **Impact:** Wasted CI runtime, false failures, and non-actionable signal because one matrix leg can never be compliant.
- **Recommended fix:** Remove `3.9` from CI matrix and gate workflow Python versions directly from project metadata (single source of truth).

## 2) Runtime dependency is optional in code-path but declared as hard runtime requirement
- **Severity:** High
- **Location:** `pyproject.toml`, `src/coloursorter/bench/serial_transport.py`, `gui/bench_app/controller.py`
- **Evidence:** `pyserial` is required only when `transport.kind == "serial"`; code raises runtime error if missing, but dependency is not modeled as an optional extra and serial connect can fail at runtime.
- **Impact:** Production startup/install ambiguity and runtime failures when switching from mock to serial mode.
- **Recommended fix:** Add `pyserial` as `project.optional-dependencies.serial`, enforce installation in serial environments, and surface preflight validation during config load when serial transport is selected.

## 3) Qt dependency validation is too weak for real runtime readiness
- **Severity:** High
- **Location:** `tools/validate_pyside6_modules.py`, `.github/workflows/ci.yml`, `tests/test_bench_controller.py`
- **Evidence:** Validator uses `find_spec` (module discoverability) rather than import/Qt runtime checks; GUI tests are skipped when PySide6 system GL deps are missing.
- **Impact:** CI can pass while production GUI still fails at runtime due to unresolved native Qt/GL dependencies.
- **Recommended fix:** In CI, add a headless smoke test that instantiates `QApplication` with `QT_QPA_PLATFORM=offscreen` and fails on import/runtime errors; install required OS packages for Qt/GL on runners.

## 4) Per-frame calibration file load inside hot path
- **Severity:** High
- **Location:** `src/coloursorter/deploy/pipeline.py`
- **Evidence:** `load_calibration(...)` is called in `PipelineRunner.run(...)` for every frame.
- **Impact:** Repeated disk I/O and parsing in the processing loop increases latency variance and lowers throughput.
- **Recommended fix:** Cache calibration in `PipelineRunner` with explicit reload triggers (file mtime watcher, manual reload command, or startup-only immutable config).

## 5) Hardcoded control constants bypass runtime config
- **Severity:** Medium
- **Location:** `gui/bench_app/controller.py`
- **Evidence:** Trigger threshold, belt speed, and encoder geometry are hardcoded (`0.5`, `140.0`, `2048`, `210.0`) instead of sourced from runtime config.
- **Impact:** Environment drift and production behavior inconsistency between docs/configs and actual execution.
- **Recommended fix:** Move these constants to `configs/bench_runtime.yaml` + `RuntimeConfig` schema, then consume only config-derived values in controller initialization.
