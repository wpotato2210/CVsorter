from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
EXPECTED_BLOCKERS = (
    "1. Invalid JSON in canonical Phase 3 evidence artifact (`docs/artifacts/phase3/phase3_evidence_bundle.json`).",
    "2. Phase 3 closure evidence declares `live_runtime` and `gui` as NOT VERIFIED.",
    "3. Required Phase 3 closure command set not fully reproducible in current environment (`run_tests.bat`, coverage gate).",
)


def test_p3_gk_004_phase3_blockers_are_canonical_and_deterministically_ordered() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    marker = "## PHASE 4 BLOCKERS"
    assert marker in report
    section = report.split(marker, maxsplit=1)[1]

    numbered_lines = tuple(
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith(("1. ", "2. ", "3. "))
    )

    assert numbered_lines[: len(EXPECTED_BLOCKERS)] == EXPECTED_BLOCKERS
