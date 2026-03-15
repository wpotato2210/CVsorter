from __future__ import annotations

from pathlib import Path


CLOSURE_REPORT_PATH = Path("docs/artifacts/phase3/phase3_closure_report.md")
REQUIRED_CHECKS = ("hil_repeatability", "protocol_parity", "timing_envelope", "trigger_correlation")
REQUIRED_GATES = (
    "| Firmware unit tests | `./run_tests.bat` | BLOCKED |",
    "| Host test suite | `pytest tests/` | PASS |",
    "| Integration timing/trace checks | `pytest bench/` | PASS |",
    "| Coverage artifact gate | `pytest --cov=src/coloursorter --cov-report=xml` | BLOCKED |",
)


def test_p3_aud_002_phase3_closure_report_contains_required_audit_contract() -> None:
    report = CLOSURE_REPORT_PATH.read_text(encoding="utf-8")

    assert "Task: T3-006" in report
    assert "Overall readiness decision: **CONDITIONAL PASS**" in report

    for check_name in REQUIRED_CHECKS:
        assert f"- {check_name}: " in report

    for gate_row in REQUIRED_GATES:
        assert gate_row in report

    assert "pytest-cov" in report
    assert "Permission denied" in report
