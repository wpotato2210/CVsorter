#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
SYSTEM_SITE_PACKAGES="${SYSTEM_SITE_PACKAGES:-1}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[setup] Python executable not found: $PYTHON_BIN" >&2
  exit 1
fi

venv_args=()
if [[ "$SYSTEM_SITE_PACKAGES" == "1" ]]; then
  venv_args+=(--system-site-packages)
fi

"$PYTHON_BIN" -m venv "${venv_args[@]}" "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if python -m pip install -e .; then
  echo "[setup] Installed with dependency resolution."
elif python -m pip install --no-build-isolation -e .; then
  echo "[setup] Installed without build isolation."
else
  echo "[setup] Falling back to offline-style editable install without dependency resolution." >&2
  python -m pip install --no-build-isolation --no-deps -e .
fi

echo "[setup] Complete. Activate with: source $VENV_DIR/bin/activate"
