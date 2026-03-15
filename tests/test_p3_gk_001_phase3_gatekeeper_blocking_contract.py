from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
EXPECTED_BLOCKERS = (
    "1. Invalid JSON in canonical Phase 3 evidence artifact (`docs/artifacts/phase3/phase3_evidence_bundle.json`).",
    "2. Phase 3 closure evidence declares `live_runtime` and `gui` as NOT VERIFIED.",
    "3. Required Phase 3 closure command set not fully reproducible in current environment (`run_tests.bat`, coverage gate).",
)


def test_p3_gk_001_gatekeeper_blocks_phase_close_when_blockers_exist() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## PHASE 4 BLOCKERS" in report
    assert "## RECOMMENDATIONS" in report
    assert "**DO NOT CLOSE PHASE 3**" in report

    blockers_section = report.split("## PHASE 4 BLOCKERS", maxsplit=1)[1].split(
        "## RECOMMENDATIONS", maxsplit=1
    )[0]

    blocker_lines = [line.strip() for line in blockers_section.splitlines() if line.strip()]
    numbered_blockers = [line for line in blocker_lines if line[0].isdigit() and line[1:3] == ". "]

    assert tuple(numbered_blockers) == EXPECTED_BLOCKERS
