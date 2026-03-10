from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys



def _load_validate_function():
    import importlib.util

    script_path = Path(__file__).resolve().parents[1] / "scripts/run_phase_with_audit.py"
    spec = importlib.util.spec_from_file_location("run_phase_with_audit", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_log_completeness


def test_phase1_audit_wrapper_emits_required_events(tmp_path: Path) -> None:
    run_script = tmp_path / "run_ok.py"
    run_script.write_text("from __future__ import annotations\nprint('ok')\n", encoding="utf-8")
    calibration = tmp_path / "calibration.json"
    lane_config = tmp_path / "lane.yaml"
    calibration.write_text('{"calibration": 1}\n', encoding="utf-8")
    lane_config.write_text('lanes: [1,2]\n', encoding="utf-8")

    wrapper_script = Path(__file__).resolve().parents[1] / "scripts/run_phase_with_audit.py"
    cmd = [
        sys.executable,
        str(wrapper_script),
        "--phase",
        "phase1",
        "--run-id",
        "test-run-001",
        "--operator-id",
        "operator-A",
        "--run-mode",
        "test",
        "--test-batch-id",
        "batch-1",
        "--camera-recipe",
        "cam-default",
        "--lighting-recipe",
        "light-default",
        "--detector-provider",
        "fixed",
        "--detector-threshold",
        "0.8",
        "--calibration-path",
        str(calibration),
        "--lane-config-path",
        str(lane_config),
        "--run-script",
        str(run_script),
    ]
    completed = subprocess.run(cmd, cwd=tmp_path, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr

    log_path = tmp_path / "audit_log_phase1.jsonl"
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert entries[0]["event"] == "run_start"
    assert entries[1]["event"] == "recipe_selection"
    assert entries[2]["event"] == "threshold_binding"
    assert entries[3]["event"] == "calibration_binding"
    assert entries[-1]["event"] == "run_end"
    assert entries[3]["calibration_hash"]
    assert entries[3]["lane_config_hash"]
    assert entries[-1]["status"] == "success"

    validate_log_completeness = _load_validate_function()
    valid, errors = validate_log_completeness(log_path, "test-run-001")
    assert valid, errors


def test_validate_log_completeness_detects_missing_events(tmp_path: Path) -> None:
    log_path = tmp_path / "audit_log_phase1.jsonl"
    log_path.write_text(
        json.dumps({"run_id": "abc", "event": "run_start"}) + "\n",
        encoding="utf-8",
    )

    validate_log_completeness = _load_validate_function()
    valid, errors = validate_log_completeness(log_path, "abc")
    assert not valid
    assert any("missing required event" in err for err in errors)
