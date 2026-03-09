# Phase 1 Beginner Execution Guide

This guide is derived from repository-local Phase 1 definitions and readiness notes.

## 1) Repository inspection summary

### Project structure (high level)
- `src/coloursorter/` — main Python package for bench runtime, config parsing, protocol logic, scheduling, deployment pipeline, and runtime wrappers.
- `tests/` — pytest coverage including dedicated `test_phase1_quality_gate.py`.
- `configs/` — runtime and calibration/lane configuration used by bench/live flows.
- `tools/` and `scripts/` — readiness checks and acceptance helpers.
- `docs/` — roadmap, Phase 1 plan, and readiness assessment artifacts.

### Languages and build/test stack
- Primary language: Python (`pyproject.toml` package + console scripts).
- Secondary language: C for firmware under `firmware/mcu/`.
- Test runner: `pytest`.

### Main application entry points
- Module entry: `python -m coloursorter` (`src/coloursorter/__main__.py`).
- Scenario CLI entry point: `coloursorter-bench-cli`.
- Bench GUI entry point: `coloursorter-bench-gui`.

### README instructions relevant to Phase 1
- Install with editable package and optional dev dependencies.
- Verify with `coloursorter-bench-cli --scenario nominal --avg-rtt-ms 10 --peak-rtt-ms 20`.
- Run full suite with `pytest -q`.

### TODO/incomplete module notes
- There are no open `TODO`/`FIXME` markers in `src/` directly tied to Phase 1 closure.
- `model_stub` is intentionally a baseline provider option, not an untracked TODO.
- `train` package is explicitly non-runtime for Phase 1.

### What the project currently does
The current repository already provides deterministic bench execution (replay and live), config-driven runtime behavior, scenario threshold evaluation, artifact generation, and transport interfaces with tests.

### What Phase 1 requires
Phase 1 is explicitly defined in `docs/high_priority_baseline_bean_sorting_plan.md` items 1..7:
1. Replay-mode setup <= 3 minutes.
2. Calibration reliability >= 98% over 50 replay sessions.
3. Decision/schedule payload schema validity = 100%.
4. Artifact parameter override completeness = 100%.
5. Scenario thresholds pass/fail coverage for all configured thresholds.
6. Detection provider override reliability = 100%.
7. Mock vs serial protocol-shape parity mismatch count = 0.

## 2) Remaining Phase 1 tasks (status)

Reference source: `docs/phase1_readiness_assessment.md` verification matrix.

### Task: Replay-mode setup timing evidence
- Status: **partial**
- Files involved: `src/coloursorter/__main__.py`, `src/coloursorter/bench/cli.py`, `docs/phase1_readiness_assessment.md`
- Dependencies: replay dataset in `data/` or configured replay path, Python environment, artifacts directory write permission.

### Task: Calibration reliability campaign (50 runs, >=98%)
- Status: **partial**
- Files involved: `scripts/run_acceptance_suite.py`, `configs/bench_runtime.yaml`, `docs/phase1_readiness_assessment.md`
- Dependencies: stable replay calibration dataset, repeatable environment, artifact persistence.

### Task: Decision/schedule payload acceptance-log evidence
- Status: **partial**
- Files involved: `contracts/sched_schema.json`, `contracts/mcu_response_schema.json`, `tests/test_phase1_quality_gate.py`, artifact outputs under `artifacts/`
- Dependencies: replay runs producing events/telemetry; schema validation tooling.

### Task: Artifact parameter-override completeness evidence
- Status: **partial**
- Files involved: `scripts/run_acceptance_suite.py`, `tools/validate_artifacts.py`, artifact outputs under `artifacts/`
- Dependencies: successful benchmark run with configuration overrides.

### Task: Scenario threshold full evidence bundle
- Status: **partial**
- Files involved: `src/coloursorter/bench/scenario_runner.py`, `scripts/run_acceptance_suite.py`, `artifacts/scenario_threshold_report.json`
- Dependencies: runnable CLI environment and generated threshold report.

### Task: Detection provider override evidence matrix
- Status: **partial**
- Files involved: `src/coloursorter/deploy/detection.py`, `tests/test_detection_providers.py`, acceptance artifacts metadata.
- Dependencies: acceptance runs executed with each provider (`opencv_basic`, `opencv_calibrated`, `model_stub`).

### Task: Mock vs serial transport parity gate
- Status: **complete (code/test gate)**
- Files involved: `tools/transport_parity_check.py`, `tests/test_phase1_quality_gate.py`, `tests/test_transport_contract.py`
- Dependencies: transport parity report generation remains part of release evidence.

## 3) Execution plan for each remaining task

> These commands are explicit and executable from repository root.

### TASK: Replay-mode setup timing evidence

Goal:
Measure and document command-start to first processed frame timing as <= 180 seconds.

Files involved:
- `/workspace/CVsorter/src/coloursorter/__main__.py`
- `/workspace/CVsorter/src/coloursorter/bench/cli.py`
- `/workspace/CVsorter/artifacts/`

Step-by-step instructions:
1. Open terminal.
2. Clone repository if needed:
   ```bash
   git clone https://github.com/wpotato2210/CVsorter.git
   ```
3. Enter repository:
   ```bash
   cd CVsorter
   ```
4. Create branch:
   ```bash
   git checkout -b phase1-replay-timing-evidence
   ```
5. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .[dev]
   ```
6. Run replay command and collect timestamps:
   ```bash
   /usr/bin/time -p python -m coloursorter --mode replay --source data --artifact-root artifacts/phase1_replay_timing --max-cycles 60
   ```
7. Save terminal output to file:
   ```bash
   /usr/bin/time -p python -m coloursorter --mode replay --source data --artifact-root artifacts/phase1_replay_timing --max-cycles 60 2>&1 | tee artifacts/phase1_replay_timing/run.log
   ```
8. Confirm timing is <= 180 seconds from `real` value in output.

Expected output:
- Exit code `0`.
- Artifact files in `artifacts/phase1_replay_timing/`.
- `real < 180` in timing output.

### TASK: Calibration reliability campaign

Goal:
Run 50 replay sessions and verify success rate >= 98%.

Files involved:
- `/workspace/CVsorter/scripts/run_acceptance_suite.py`
- `/workspace/CVsorter/artifacts/calibration_reliability_report.json`

Step-by-step instructions:
1. Open terminal.
2. Ensure repository is available and entered:
   ```bash
   cd CVsorter
   ```
3. Create branch:
   ```bash
   git checkout -b phase1-calibration-reliability
   ```
4. Install dependencies:
   ```bash
   python -m pip install -e .[dev]
   ```
5. Run the acceptance suite:
   ```bash
   python scripts/run_acceptance_suite.py
   ```
6. Inspect calibration report:
   ```bash
   python -c "import json; d=json.load(open('artifacts/calibration_reliability_report.json')); print(d['successful_runs'], d['total_runs'], d['reliability_percent'])"
   ```
7. Verify `reliability_percent >= 98.0`.

Expected output:
- `artifacts/calibration_reliability_report.json` exists.
- Report shows at least 49 successful runs out of 50.

### TASK: Decision/schedule payload validity evidence

Goal:
Prove acceptance logs contain schema-compliant payload fields with zero missing lane/reject/schedule fields.

Files involved:
- `/workspace/CVsorter/contracts/sched_schema.json`
- `/workspace/CVsorter/contracts/mcu_response_schema.json`
- `/workspace/CVsorter/artifacts/`

Step-by-step instructions:
1. Open terminal.
2. Enter repository:
   ```bash
   cd CVsorter
   ```
3. Create branch:
   ```bash
   git checkout -b phase1-payload-validity-evidence
   ```
4. Generate fresh artifacts:
   ```bash
   python scripts/run_acceptance_suite.py
   ```
5. Validate artifacts and protocol shape:
   ```bash
   python tools/validate_artifacts.py --artifacts artifacts
   python tools/transport_parity_check.py --artifacts artifacts
   ```
6. Confirm no schema/protocol shape mismatches in generated reports.

Expected output:
- `artifact_validation_report.json` indicates pass.
- `transport_parity_report.json` indicates `shape_match: true`.

### TASK: Artifact parameter-override completeness evidence

Goal:
Confirm every runtime override is captured in artifacts with timestamp and source.

Files involved:
- `/workspace/CVsorter/tools/validate_artifacts.py`
- `/workspace/CVsorter/artifacts/artifact_validation_report.json`

Step-by-step instructions:
1. Open terminal.
2. Enter repository:
   ```bash
   cd CVsorter
   ```
3. Create branch:
   ```bash
   git checkout -b phase1-artifact-completeness
   ```
4. Run suite to emit artifacts:
   ```bash
   python scripts/run_acceptance_suite.py
   ```
5. Validate artifact completeness:
   ```bash
   python tools/validate_artifacts.py --artifacts artifacts
   ```
6. Open report and verify `overall_ok` is true.

Expected output:
- `artifacts/artifact_validation_report.json` contains completeness pass.

### TASK: Scenario threshold full evidence

Goal:
Generate scenario coverage report where all configured thresholds emit pass/fail without skipped entries.

Files involved:
- `/workspace/CVsorter/src/coloursorter/bench/scenario_runner.py`
- `/workspace/CVsorter/artifacts/scenario_threshold_report.json`

Step-by-step instructions:
1. Open terminal.
2. Enter repository:
   ```bash
   cd CVsorter
   ```
3. Create branch:
   ```bash
   git checkout -b phase1-scenario-threshold-evidence
   ```
4. Run scenario commands:
   ```bash
   coloursorter-bench-cli --scenario nominal --avg-rtt-ms 10 --peak-rtt-ms 20
   coloursorter-bench-cli --scenario latency_stress --avg-rtt-ms 10 --peak-rtt-ms 20
   coloursorter-bench-cli --scenario fault_to_safe --avg-rtt-ms 10 --peak-rtt-ms 20 --safe-transitions 1
   coloursorter-bench-cli --scenario recovery_flow --avg-rtt-ms 10 --peak-rtt-ms 20 --safe-transitions 1 --recovered-from-safe
   ```
5. Optionally generate unified report via:
   ```bash
   python scripts/run_acceptance_suite.py
   ```
6. Confirm all configured scenarios are present in report output.

Expected output:
- Pass/fail line for each scenario.
- No missing scenario rows.

### TASK: Detection provider override reliability evidence

Goal:
Verify provider selection and output metadata match requested provider for all acceptance runs.

Files involved:
- `/workspace/CVsorter/src/coloursorter/deploy/detection.py`
- `/workspace/CVsorter/tests/test_detection_providers.py`
- `/workspace/CVsorter/artifacts/`

Step-by-step instructions:
1. Open terminal.
2. Enter repository:
   ```bash
   cd CVsorter
   ```
3. Create branch:
   ```bash
   git checkout -b phase1-provider-override-matrix
   ```
4. Run deterministic provider unit tests:
   ```bash
   pytest -q tests/test_detection_providers.py
   ```
5. Run acceptance suite once per provider by editing `configs/bench_runtime.yaml` `detection.provider` value and rerunning:
   ```bash
   python scripts/run_acceptance_suite.py
   ```
6. Save each run's report under unique folder names (`artifacts/provider_opencv_basic`, etc.).

Expected output:
- All provider test cases pass.
- Acceptance metadata provider name matches configured provider in each run.

## 4) GitHub workflow (exact)

1. Stage changes:
   ```bash
   git add .
   ```
2. Commit:
   ```bash
   git commit -m "complete phase 1 task"
   ```
3. Push:
   ```bash
   git push origin phase1-task-name
   ```
4. Create pull request in browser:
   - Open your repository on GitHub.
   - Click **Compare & pull request** for your branch (appears after push).
   - Verify base branch is `main` (or project default branch).
   - Set title: `Phase 1: <task name> evidence and validation`.
   - In description, include: objective, commands run, artifact paths, pass/fail summary.
   - Click **Create pull request**.

## 5) Verification that Phase 1 is complete

Run these checks:
```bash
pytest -q
python tools/protocol_static_guard.py
python tools/firmware_readiness_check.py --strict
python tools/validate_pyside6_modules.py
python tools/hardware_readiness_report.py --strict
python scripts/run_acceptance_suite.py
```

Expected behaviors:
- All commands exit with code `0`.
- `artifacts/phase1_readiness_summary.md` ends with recommendation `PASS`.
- `artifacts/calibration_reliability_report.json` shows `reliability_percent >= 98.0`.
- `artifacts/transport_parity_report.json` shows zero shape mismatch.
- Scenario report lists every configured scenario.

Expected evidence files:
- `artifacts/environment_checks.json`
- `artifacts/replay_campaign_summary.json`
- `artifacts/calibration_reliability_report.json`
- `artifacts/artifact_validation_report.json`
- `artifacts/scenario_threshold_report.json`
- `artifacts/transport_parity_report.json`
- `artifacts/phase1_readiness_summary.md`

## 6) Final checklist

- [ ] Replay setup time evidence (<= 180s) captured.
- [ ] Calibration campaign complete (50 runs, >= 98%).
- [ ] Payload schema validity evidence archived.
- [ ] Artifact completeness evidence archived.
- [ ] Scenario threshold evidence archived.
- [ ] Provider override matrix archived.
- [ ] Transport parity evidence archived.
- [ ] Final summary says `PASS`.

Final working state:
- Repo tests and readiness gates pass.
- Phase 1 quantitative evidence artifacts are present and auditable.
- Phase 1 exit decision can be made from reproducible command outputs.
