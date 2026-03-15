from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
EXPECTED_BLOCKER = (
    "3. Required Phase 3 closure command set not fully reproducible in current environment "
    "(`run_tests.bat`, coverage gate)."
)


def test_p3_gk_003_gatekeeper_lists_command_reproducibility_blocker() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## PHASE 4 BLOCKERS" in report
    assert EXPECTED_BLOCKER in report
    assert "**DO NOT CLOSE PHASE 3**" in report
