from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
EXPECTED_DEBT_ROWS = (
    "| Invalid committed `phase3_evidence_bundle.json` | HIGH | Phase closeout artifact is non-machine-readable and cannot be consumed by automated governance checks. |",
    "| Live-runtime and GUI explicitly NOT VERIFIED in Phase 3 bundle/closure docs | HIGH | Phase gate evidence is incomplete for full-system closeout semantics. |",
    "| Windows-only `run_tests.bat` gate blocked on Linux runner shells | MEDIUM | Required command in closure checklist is not cross-platform executable without wrapper or platform-specific handling. |",
    "| Local coverage gate command blocked due missing plugin in environment | MEDIUM | Coverage exit check cannot be reproduced unless test extras are installed. |",
    "| Existing xfail usage in safety/scaffold areas | MEDIUM | Known behavior gaps can hide regressions if left untriaged. |",
)


def test_p3_gk_007_phase3_gatekeeper_technical_debt_table_is_complete() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## TECHNICAL DEBT" in report
    assert "## PHASE 4 BLOCKERS" in report

    technical_debt_section = report.split("## TECHNICAL DEBT", maxsplit=1)[1].split(
        "## PHASE 4 BLOCKERS", maxsplit=1
    )[0]

    for row in EXPECTED_DEBT_ROWS:
        assert row in technical_debt_section

    assert technical_debt_section.count("| HIGH |") == 2
    assert technical_debt_section.count("| MEDIUM |") == 3
