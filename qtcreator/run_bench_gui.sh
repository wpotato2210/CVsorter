#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}/gui${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -n "${QT_QPA_PLATFORM:-}" ]]; then
  export QT_QPA_PLATFORM
fi
exec python "${ROOT_DIR}/gui/bench_app/app.py" --config "${ROOT_DIR}/configs/bench_runtime.yaml"
