#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "[run] Missing virtualenv at $VENV_DIR. Run ./setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

exec coloursorter-bench-cli --scenario nominal --avg-rtt-ms 9 --peak-rtt-ms 15
