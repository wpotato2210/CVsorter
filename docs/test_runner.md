# ColourSorter Test Runner

## Overview
`ColourSorterTestRunner.exe` is a standalone PySide6 desktop tool for non-developers to run validation and export logs.

## Build executable
1. Install dependencies: `pip install pyinstaller pyside6`.
2. From repo root run:
   ```bash
   python scripts/build_test_runner_exe.py
   ```
3. Output executable: `dist/ColourSorterTestRunner.exe`.

## Operator workflow
1. Double-click `ColourSorterTestRunner.exe`.
2. Click **Run Full Acceptance Suite**.
3. Watch live progress and PASS/FAIL status.
4. Click **Export Report Bundle** to create `artifacts/test_report_bundle.zip`.

## Buttons and outputs
- **Run Quick Check**: runs pytest + protocol/firmware/gui/hardware checks.
- **Run Full Acceptance Suite**: executes `scripts/run_acceptance_suite.py` and displays READY/NOT READY summary.
- **Run Replay Campaign**: replay mode runs using configured dataset and run count.
- **Run Calibration Campaign**: executes acceptance suite calibration path.
- **Run Scenario Evaluator**: runs scenario threshold tests.
- **Run Transport Parity Check**: runs parity checker.
- **Validate Replay Dataset**: runs `tools/validate_replay_dataset.py`.
- **Environment Diagnostics**: generates `artifacts/environment_report.json`.
- **Compare Runs**: creates `artifacts/run_comparison_report.md` from two run folders.
- **Export Report Bundle**: zips logs/reports into `artifacts/test_report_bundle.zip`.
- **Check for Updates**: compares local tag with origin tags and notifies operator.

## Run artifact layout
Each action creates:
- `artifacts/run_YYYY_MM_DD_HH_MM_SS/console.log`
- `artifacts/run_YYYY_MM_DD_HH_MM_SS/configuration_snapshot.json`

Global artifacts include:
- `artifacts/run_snapshot.json`
- `artifacts/failure_analysis.md` (on failure)
- `artifacts/performance_metrics.json`
- `artifacts/environment_report.json`
- `artifacts/run_comparison_report.md`

## Safe mode
Enable **Safe Mode** toggle to force replay-only behavior and disable hardware communication through environment flags.

## Portable mode
Run with `--portable`:
```bash
ColourSorterTestRunner.exe --portable
```
Artifacts are saved next to the executable for no-install usage.

## Updates
**Check for Updates** reads git tags (`git describe` and `git ls-remote`) and informs operators if a newer tag exists. Updating scripts/datasets/scenario packs is done by syncing the repository.
