@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "REPORT_DIR=test_reports"
set "REPORT_FILE=%REPORT_DIR%\test_results.txt"
set "USE_PYTEST=0"
set "HARNESS_FAILURE=0"

if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"

echo ================================================== > "%REPORT_FILE%"
echo CVsorter Windows Test Harness >> "%REPORT_FILE%"
echo Start: %DATE% %TIME% >> "%REPORT_FILE%"
echo Working directory: %CD% >> "%REPORT_FILE%"
echo ================================================== >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

echo [harness] Checking Python availability...
python --version >> "%REPORT_FILE%" 2>&1
if errorlevel 1 (
  echo [harness] FAIL: Python is not available.
  echo FAIL: Python is not available. >> "%REPORT_FILE%"
  set "HARNESS_FAILURE=1"
  goto :summary
)

echo [harness] Detecting pytest...
python -c "import pytest" >> "%REPORT_FILE%" 2>&1
if errorlevel 1 (
  echo [harness] pytest not found; using unittest discovery.
  echo Test runner: unittest >> "%REPORT_FILE%"
  echo Command: python -m unittest discover -s tests -p test_*.py -v >> "%REPORT_FILE%"
  python -m unittest discover -s tests -p test_*.py -v >> "%REPORT_FILE%" 2>&1
  if errorlevel 1 set "HARNESS_FAILURE=1"
) else (
  set "USE_PYTEST=1"
  echo [harness] pytest detected; running full suite.
  echo Test runner: pytest >> "%REPORT_FILE%"
  echo Command: python -m pytest tests/ bench/ >> "%REPORT_FILE%"
  python -m pytest tests/ bench/ >> "%REPORT_FILE%" 2>&1
  if errorlevel 1 set "HARNESS_FAILURE=1"
)

:summary
echo. >> "%REPORT_FILE%"
echo End: %DATE% %TIME% >> "%REPORT_FILE%"
if "%HARNESS_FAILURE%"=="0" (
  echo Summary: PASS >> "%REPORT_FILE%"
  echo [harness] PASS: all tests completed successfully.
  echo [harness] Results saved to %REPORT_FILE%
  exit /b 0
)

echo Summary: FAIL >> "%REPORT_FILE%"
echo [harness] FAIL: one or more checks failed.
echo [harness] Results saved to %REPORT_FILE%
exit /b 1
