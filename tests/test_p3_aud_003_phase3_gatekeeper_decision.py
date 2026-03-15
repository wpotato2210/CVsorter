from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
REQUIRED_PHASE4_BLOCKERS = (
    "1. Invalid JSON in canonical Phase 3 evidence artifact (`docs/artifacts/phase3/phase3_evidence_bundle.json`).",
    "2. Phase 3 closure evidence declares `live_runtime` and `gui` as NOT VERIFIED.",
    "3. Required Phase 3 closure command set not fully reproducible in current environment (`run_tests.bat`, coverage gate).",
)


def test_p3_aud_003_phase3_gatekeeper_audit_declares_do_not_close_with_blockers() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## FINAL PHASE GATE DECISION" in report
    assert "**DO NOT CLOSE PHASE 3**" in report

    for blocker in REQUIRED_PHASE4_BLOCKERS:
        assert blocker in report
