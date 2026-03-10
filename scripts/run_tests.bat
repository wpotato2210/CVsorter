@echo off
setlocal enabledelayedexpansion

set PYTHON_STATUS=0
set FIRMWARE_STATUS=0

cd /d %~dp0\..

echo [1/5] Installing Python test dependencies
python -m pip install -q -e .[test]
if errorlevel 1 echo Python dependency install skipped due environment/network limitations

echo [2/5] Running Python tests
if not exist test_data\coverage\python mkdir test_data\coverage\python
python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pytest_cov') else 1)"
if errorlevel 1 (
  echo pytest-cov not installed; running without coverage
  set PYTEST_COV_ARGS=
) else (
  set PYTEST_COV_ARGS=--cov=src/coloursorter --cov-report=term-missing --cov-report=xml:test_data/coverage/python/coverage.xml
)
set PYTHONPATH=src
python -m pytest tests/automation/python %PYTEST_COV_ARGS%
if errorlevel 1 set PYTHON_STATUS=1

echo [3/5] Building firmware GoogleTest suite
if not exist test_data\build\firmware_gtest mkdir test_data\build\firmware_gtest
where cmake >nul 2>nul
if errorlevel 1 (
  echo Firmware tests skipped: cmake not found
  set FIRMWARE_STATUS=2
) else (
  cmake -S tests/automation/firmware -B test_data/build/firmware_gtest -DENABLE_COVERAGE=ON >nul 2>nul
  if errorlevel 1 (
    echo Firmware tests skipped: GoogleTest/CMake dependency missing
    set FIRMWARE_STATUS=2
  ) else (
    cmake --build test_data/build/firmware_gtest >nul 2>nul
    if errorlevel 1 set FIRMWARE_STATUS=1
  )
)

echo [4/5] Running firmware tests
if %FIRMWARE_STATUS%==0 (
  ctest --test-dir test_data/build/firmware_gtest --output-on-failure
  if errorlevel 1 set FIRMWARE_STATUS=1
)

echo [5/5] Coverage artifact generation
where lcov >nul 2>nul
if %FIRMWARE_STATUS%==0 if not errorlevel 1 (
  if not exist test_data\coverage\firmware mkdir test_data\coverage\firmware
  lcov --capture --directory test_data/build/firmware_gtest --output-file test_data/coverage/firmware/lcov.info >nul 2>nul
)

set TOTAL_STATUS=0
if not %PYTHON_STATUS%==0 set TOTAL_STATUS=1
if %FIRMWARE_STATUS%==1 set TOTAL_STATUS=1

echo.
echo ========== TEST SUMMARY ==========
if %PYTHON_STATUS%==0 (
  echo Python tests: PASS
) else (
  echo Python tests: FAIL
)
if %FIRMWARE_STATUS%==0 (
  echo Firmware tests: PASS
) else if %FIRMWARE_STATUS%==2 (
  echo Firmware tests: SKIPPED ^(missing host gtest toolchain^)
) else (
  echo Firmware tests: FAIL
)
if %TOTAL_STATUS%==0 (
  echo Overall: PASS
) else (
  echo Overall: FAIL
)
echo Python coverage: test_data/coverage/python/coverage.xml ^(when pytest-cov available^)
if exist test_data\coverage\firmware\lcov.info (
  echo Firmware coverage: test_data/coverage/firmware/lcov.info
) else (
  echo Firmware coverage: unavailable
)

exit /b %TOTAL_STATUS%
