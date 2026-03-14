from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path



FIXTURE_PATH = Path("tests/fixtures/hil_gate_t3_004.json")


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise AssertionError("fixture runs must be a list")
    return payload


def test_t3_004_fixture_is_seeded_and_ordered() -> None:
    payload = _load_fixture()

    assert payload["vector_pack"] == "T3-004"
    assert payload["seed"] == 3004

    runs = payload["runs"]
    scenario_run_pairs = [
        (str(run["scenario_id"]), int(run["run_index"])) for run in runs
    ]
    assert scenario_run_pairs == [
        ("stable_reject_path", 1),
        ("stable_reject_path", 2),
        ("stable_accept_path", 1),
        ("stable_accept_path", 2),
    ]


def test_t3_004_tool_is_deterministic_across_reruns() -> None:
    command = [sys.executable, "tools/hil_informational_gate.py"]

    first = subprocess.run(command, check=False, capture_output=True, text=True)
    second = subprocess.run(command, check=False, capture_output=True, text=True)

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["gate_passed"] is True
    assert report["gate_failures"] == []
    assert report["informational_only"] is False


def test_t3_004_hil_enforcement_release_gating() -> None:
    payload = _load_fixture()
    command = [
        sys.executable,
        "tools/hil_informational_gate.py",
        "--fixture",
        str(FIXTURE_PATH),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr

    report = json.loads(completed.stdout)
    assert report["gate_passed"] is True
    assert report["gate_failures"] == []
    assert report["vector_pack"] == "T3-004"
    assert report["seed"] == 3004
