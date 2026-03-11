#!/usr/bin/env bash
set -u

PYTHON_STATUS=0
FIRMWARE_STATUS=0

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

echo "[1/6] Running docs wrapper lint"
if ! python tools/check_docs_wrappers.py; then
  echo "Docs wrapper lint failed"
  exit 1
fi

echo "[2/6] Installing Python test dependencies"
if ! python -m pip install -q -e '.[test]'; then
  echo "Python dependency install skipped due environment/network limitations"
fi

PY_TEST_TARGET="tests/automation/python"
PY_COV_DIR="test_data/coverage/python"
mkdir -p "$PY_COV_DIR"

echo "[3/6] Running Python tests"
PYTEST_ARGS=("$PY_TEST_TARGET")
if PYTHONPATH=src python - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec('pytest_cov') else 1)
PY
then
  PYTEST_ARGS+=(--cov=src/coloursorter --cov-report=term-missing --cov-report="xml:$PY_COV_DIR/coverage.xml")
else
  echo "pytest-cov not installed; running without coverage"
fi
if ! PYTHONPATH=src python -m pytest "${PYTEST_ARGS[@]}"; then
  PYTHON_STATUS=1
fi

echo "[4/6] Building firmware GoogleTest suite"
FW_BUILD_DIR="test_data/build/firmware_gtest"
mkdir -p "$FW_BUILD_DIR"
if command -v cmake >/dev/null 2>&1; then
  if cmake -S tests/automation/firmware -B "$FW_BUILD_DIR" -DENABLE_COVERAGE=ON >/tmp/cvsorter_fw_cmake.log 2>&1; then
    cmake --build "$FW_BUILD_DIR" >/tmp/cvsorter_fw_build.log 2>&1 || FIRMWARE_STATUS=1
  else
    echo "Firmware tests skipped: GoogleTest/CMake dependency missing"
    FIRMWARE_STATUS=2
  fi
else
  echo "Firmware tests skipped: cmake not found"
  FIRMWARE_STATUS=2
fi

echo "[5/6] Running firmware tests"
if [ "$FIRMWARE_STATUS" -eq 0 ]; then
  ctest --test-dir "$FW_BUILD_DIR" --output-on-failure || FIRMWARE_STATUS=1
fi

echo "[6/6] Coverage artifact generation"
if [ "$FIRMWARE_STATUS" -eq 0 ] && command -v lcov >/dev/null 2>&1; then
  mkdir -p test_data/coverage/firmware
  lcov --capture --directory "$FW_BUILD_DIR" --output-file test_data/coverage/firmware/lcov.info >/tmp/cvsorter_lcov.log 2>&1 || true
fi

TOTAL_STATUS=0
if [ "$PYTHON_STATUS" -ne 0 ] || [ "$FIRMWARE_STATUS" -eq 1 ]; then
  TOTAL_STATUS=1
fi

echo ""
echo "========== TEST SUMMARY =========="
[ "$PYTHON_STATUS" -eq 0 ] && echo "Python tests: PASS" || echo "Python tests: FAIL"
if [ "$FIRMWARE_STATUS" -eq 0 ]; then
  echo "Firmware tests: PASS"
elif [ "$FIRMWARE_STATUS" -eq 2 ]; then
  echo "Firmware tests: SKIPPED (missing host gtest toolchain)"
else
  echo "Firmware tests: FAIL"
fi
[ "$TOTAL_STATUS" -eq 0 ] && echo "Overall: PASS" || echo "Overall: FAIL"

echo "Python coverage: test_data/coverage/python/coverage.xml (when pytest-cov available)"
if [ -f test_data/coverage/firmware/lcov.info ]; then
  echo "Firmware coverage: test_data/coverage/firmware/lcov.info"
else
  echo "Firmware coverage: unavailable"
fi

exit "$TOTAL_STATUS"
