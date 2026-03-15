from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
EXPECTED_RECOMMENDATIONS = (
    "1. Regenerate and commit a valid `docs/artifacts/phase3/phase3_evidence_bundle.json` from `tools/phase3_evidence_bundle.py`.",
    "2. Add a strict JSON validity test for committed Phase 3 artifact paths.",
    "3. Add explicit Phase-3 live-runtime and GUI verification checks (or formally narrow Phase 3 acceptance scope to harness-only with signed governance exception).",
    "4. Make closure command matrix platform-aware (Windows vs Linux) and provide canonical equivalent commands.",
    "5. Require coverage gate preflight in local scripts (`pip install -e .[test]`) before closure execution.",
)


def test_p3_gk_006_phase3_gatekeeper_recommendations_are_canonical_and_ordered() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## RECOMMENDATIONS" in report
    assert "## FINAL PHASE GATE DECISION" in report

    recommendations_section = report.split("## RECOMMENDATIONS", maxsplit=1)[1].split(
        "## FINAL PHASE GATE DECISION", maxsplit=1
    )[0]

    recommendation_lines = tuple(
        line.strip()
        for line in recommendations_section.splitlines()
        if line.strip().startswith(("1. ", "2. ", "3. ", "4. ", "5. "))
    )

    assert recommendation_lines == EXPECTED_RECOMMENDATIONS
