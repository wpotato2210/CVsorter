from __future__ import annotations

from pathlib import Path


CLOSURE_REPORT_PATH = Path("docs/artifacts/phase3/phase3_closure_report.md")


def test_p3_aud_002_phase3_closure_report_declares_unverified_runtime_surfaces() -> None:
    report = CLOSURE_REPORT_PATH.read_text(encoding="utf-8")

    assert "| live runtime | PARTIAL | NOT VERIFIED |" in report
    assert "| GUI | PARTIAL | NOT VERIFIED |" in report
    assert "- NOT VERIFIED: Not directly validated by a passing Phase 3 deterministic check in this bundle." in report
