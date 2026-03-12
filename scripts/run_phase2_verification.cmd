@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TIMESTAMP=%%I"
if not defined TIMESTAMP set "TIMESTAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

set "ARTIFACT_ROOT=artifacts"
set "ARTIFACT_BENCH=%ARTIFACT_ROOT%\bench"
set "ARTIFACT_LOG_ROOT=%ARTIFACT_ROOT%\phase2_logs"
set "RUN_LOG_DIR=%ARTIFACT_LOG_ROOT%\%TIMESTAMP%"

if not exist "%ARTIFACT_ROOT%" mkdir "%ARTIFACT_ROOT%"
if not exist "%ARTIFACT_BENCH%" mkdir "%ARTIFACT_BENCH%"
if not exist "%ARTIFACT_LOG_ROOT%" mkdir "%ARTIFACT_LOG_ROOT%"
if not exist "%RUN_LOG_DIR%" mkdir "%RUN_LOG_DIR%"

set "PHASE2_TESTS_LOG=%RUN_LOG_DIR%\phase2_tests.log"
set "BENCH_REPLAY_LOG=%RUN_LOG_DIR%\bench_replay.log"
set "TRANSPORT_PARITY_LOG=%RUN_LOG_DIR%\transport_parity.log"
set "FULL_TESTS_LOG=%RUN_LOG_DIR%\full_tests.log"
set "COVERAGE_LOG=%RUN_LOG_DIR%\coverage.log"

set "TARGETED_STATUS=FAIL"
set "BENCH_STATUS=FAIL"
set "PARITY_STATUS=FAIL"
set "FULL_SUITE_STATUS=FAIL"
set "COVERAGE_STATUS=FAIL"


echo PHASE 2 VERIFICATION RUNNER

echo === Phase2 Targeted Tests ===
echo [%DATE% %TIME%] Starting Phase-2 targeted tests > "%PHASE2_TESTS_LOG%"
python -m pytest -q tests/test_preprocess.py --import-mode=importlib >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_runtime_config.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_pipeline.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_serial_interface.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_protocol_compliance_v3.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_bench_controller.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
python -m pytest -q tests/test_bench_controller_gui.py >> "%PHASE2_TESTS_LOG%" 2>&1 || exit /b 1
set "TARGETED_STATUS=PASS"

echo === Bench Replay Integration ===
set "PYTHONPATH=src"
echo [%DATE% %TIME%] Starting bench replay > "%BENCH_REPLAY_LOG%"
python -m coloursorter.bench.cli --mode replay --source data --artifact-root artifacts/bench --text-report >> "%BENCH_REPLAY_LOG%" 2>&1 || exit /b 1
set "BENCH_STATUS=PASS"

echo === Transport Parity Check ===
echo [%DATE% %TIME%] Starting transport parity check > "%TRANSPORT_PARITY_LOG%"
python tools/transport_parity_check.py --artifacts artifacts >> "%TRANSPORT_PARITY_LOG%" 2>&1 || exit /b 1
set "PARITY_STATUS=PASS"

echo === Full Test Suite ===
echo [%DATE% %TIME%] Starting full test suite > "%FULL_TESTS_LOG%"
python -m pytest tests/ >> "%FULL_TESTS_LOG%" 2>&1 || exit /b 1
set "FULL_SUITE_STATUS=PASS"

echo === Coverage Generation ===
echo [%DATE% %TIME%] Starting coverage generation > "%COVERAGE_LOG%"
pytest --cov=src/coloursorter --cov-report=xml --cov-report=term >> "%COVERAGE_LOG%" 2>&1 || exit /b 1
if not exist "coverage.xml" exit /b 1

set "COVERAGE_PERCENT="
for /f %%I in ('powershell -NoProfile -Command "$m=Select-String -Path '%COVERAGE_LOG%' -Pattern 'TOTAL\s+\d+\s+\d+\s+(\d+)%%' | Select-Object -Last 1; if ($m) { $m.Matches[0].Groups[1].Value }"') do set "COVERAGE_PERCENT=%%I"

if not defined COVERAGE_PERCENT (
  for /f %%I in ('powershell -NoProfile -Command "$xml=[xml](Get-Content -Raw 'coverage.xml'); [int][Math]::Round([double]$xml.coverage.'line-rate'*100,0)"') do set "COVERAGE_PERCENT=%%I"
)

if not defined COVERAGE_PERCENT exit /b 1

if %COVERAGE_PERCENT% GEQ 85 (
  echo Coverage check: PASS
  set "COVERAGE_STATUS=PASS"
) else (
  echo Coverage check: FAIL
  exit /b 1
)

echo.
echo ---
echo ## PHASE 2 VERIFICATION SUMMARY
echo Targeted tests: %TARGETED_STATUS%
echo Bench replay: %BENCH_STATUS%
echo Transport parity: %PARITY_STATUS%
echo Full suite: %FULL_SUITE_STATUS%
echo Coverage threshold: %COVERAGE_STATUS%
echo.
echo Artifacts produced:
echo %ARTIFACT_BENCH%\%TIMESTAMP%\
echo %ARTIFACT_ROOT%\transport_parity_report.json
echo coverage.xml
echo %RUN_LOG_DIR%\
echo.
echo PHASE 2 VERIFICATION COMPLETE

exit /b 0
