from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_bundle(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/phase3_evidence_bundle.py", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_t3_006_verify_only_reports_green_and_is_deterministic() -> None:
    first = _run_bundle("--verify-only")
    second = _run_bundle("--verify-only")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout

    payload = json.loads(first.stdout)
    assert payload["task_id"] == "T3-006"
    assert payload["overall_ok"] is True


def test_t3_006_writes_expected_bundle_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase3"
    result = _run_bundle("--output-dir", str(output_dir))

    assert result.returncode == 0, result.stderr

    bundle_path = output_dir / "phase3_evidence_bundle.json"
    report_path = output_dir / "phase3_closure_report.md"

    assert bundle_path.exists()
    assert report_path.exists()

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["overall_ok"] is True

    report = report_path.read_text(encoding="utf-8")
    assert "Task: T3-006" in report
    assert "Overall: PASS" in report
