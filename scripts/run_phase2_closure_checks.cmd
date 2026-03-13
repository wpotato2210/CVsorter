@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TIMESTAMP=%%I"
if not defined TIMESTAMP set "TIMESTAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

set "ARTIFACT_ROOT=artifacts\phase2_closure"
set "LOG_DIR=%ARTIFACT_ROOT%\logs\%TIMESTAMP%"
set "REPORT_TXT=%ARTIFACT_ROOT%\phase2_closure_report_%TIMESTAMP%.txt"

if not exist "%ARTIFACT_ROOT%" mkdir "%ARTIFACT_ROOT%"
if not exist "%ARTIFACT_ROOT%\logs" mkdir "%ARTIFACT_ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "RUN_TESTS_STATUS=FAIL"
set "PHASE2_TASK_STATUS=FAIL"
set "RELIABILITY_STATUS=FAIL"
set "HOST_TESTS_STATUS=FAIL"
set "BENCH_TESTS_STATUS=FAIL"
set "COVERAGE_STATUS=FAIL"

set "HAS_FAILURE=0"

echo [phase2-closure] Starting required checks...

call :run_check "firmware unit tests" "run_tests.bat" "%LOG_DIR%\run_tests.log" RUN_TESTS_STATUS
call :run_check "phase2 task tests" "python -m pytest tests/test_phase2_task*.py" "%LOG_DIR%\phase2_task_tests.log" PHASE2_TASK_STATUS
call :run_check "phase2 reliability gates" "python -m pytest tests/test_phase2_reliability_gate.py tests/test_phase2_lane_segmentation_robustness.py" "%LOG_DIR%\phase2_reliability.log" RELIABILITY_STATUS
call :run_check "host test suite" "python -m pytest tests/" "%LOG_DIR%\host_tests.log" HOST_TESTS_STATUS
call :run_check "bench integration tests" "python -m pytest bench/" "%LOG_DIR%\bench_tests.log" BENCH_TESTS_STATUS
call :run_check "coverage generation" "python -m pytest --cov=src/coloursorter --cov-report=xml" "%LOG_DIR%\coverage.log" COVERAGE_STATUS

if exist "coverage.xml" (
  set "COVERAGE_FILE_STATUS=PASS"
) else (
  set "COVERAGE_FILE_STATUS=FAIL"
  set "COVERAGE_STATUS=FAIL"
  set "HAS_FAILURE=1"
)

(
  echo CVsorter Phase 2 Closure Checks
  echo Timestamp: %TIMESTAMP%
  echo Working directory: %CD%
  echo.
  echo Required checks status:
  echo - run_tests.bat: !RUN_TESTS_STATUS!
  echo - pytest tests/test_phase2_task*.py: !PHASE2_TASK_STATUS!
  echo - pytest tests/test_phase2_reliability_gate.py tests/test_phase2_lane_segmentation_robustness.py: !RELIABILITY_STATUS!
  echo - pytest tests/: !HOST_TESTS_STATUS!
  echo - pytest bench/: !BENCH_TESTS_STATUS!
  echo - pytest --cov=src/coloursorter --cov-report=xml: !COVERAGE_STATUS!
  echo - coverage.xml present: !COVERAGE_FILE_STATUS!
  echo.
  echo Logs:
  echo - %LOG_DIR%\run_tests.log
  echo - %LOG_DIR%\phase2_task_tests.log
  echo - %LOG_DIR%\phase2_reliability.log
  echo - %LOG_DIR%\host_tests.log
  echo - %LOG_DIR%\bench_tests.log
  echo - %LOG_DIR%\coverage.log
  echo.
  echo What you need next:
  if "!HAS_FAILURE!"=="0" (
    echo - All required checks are green. Phase 2 closure gate is ready.
  ) else (
    echo - Fix every check marked FAIL above.
    echo - Re-run: scripts\run_phase2_closure_checks.cmd
    echo - Use the logs listed above to resolve blockers.
  )
) > "%REPORT_TXT%"

type "%REPORT_TXT%"
echo.
if "%HAS_FAILURE%"=="0" (
  echo [phase2-closure] SUCCESS: all required checks passed.
) else (
  echo [phase2-closure] FAILURE: one or more required checks failed.
)
echo [phase2-closure] Report saved to: %REPORT_TXT%
echo [phase2-closure] Logs saved under: %LOG_DIR%
echo [phase2-closure] Press any key to close this window...
pause >nul

if "%HAS_FAILURE%"=="0" (
  exit /b 0
)

exit /b 1

:run_check
set "CHECK_NAME=%~1"
set "CHECK_CMD=%~2"
set "CHECK_LOG=%~3"
set "CHECK_STATUS_VAR=%~4"

echo [phase2-closure] Running %CHECK_NAME%
echo [%DATE% %TIME%] command: %CHECK_CMD% > "%CHECK_LOG%"
call %CHECK_CMD% >> "%CHECK_LOG%" 2>&1
if errorlevel 1 (
  set "%CHECK_STATUS_VAR%=FAIL"
  set "HAS_FAILURE=1"
  echo [phase2-closure] FAIL - %CHECK_NAME%
) else (
  set "%CHECK_STATUS_VAR%=PASS"
  echo [phase2-closure] PASS - %CHECK_NAME%
)

goto :eof
