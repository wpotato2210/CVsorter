from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
REQUIRED_SECTION_ORDER = (
    "## PHASE 4 BLOCKERS",
    "## RECOMMENDATIONS",
    "## FINAL PHASE GATE DECISION",
)


def test_p3_gk_005_gatekeeper_decision_is_traceable_to_blockers_and_recommendations() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    positions = [report.find(section) for section in REQUIRED_SECTION_ORDER]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)
    assert "**DO NOT CLOSE PHASE 3**" in report
    assert (
        "Reason: high-severity evidence integrity and verification-scope gaps remain; "
        "beginning Phase 4 would compound risk on unstable or unverified closure assumptions."
        in report
    )
