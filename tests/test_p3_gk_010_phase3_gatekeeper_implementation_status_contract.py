from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
REQUIRED_STATUS_LINES = (
    "- Phase scope source: canonical Phase 3 closure in `docs/phase3_4_5_safe_task_board.md` requires T3-001..T3-006 and evidence bundle generation.",
    "- Roadmap source still defines deeper firmware/runtime scope (Phase 3.1..3.5) in `docs/deterministic_execution_roadmap.md` (firmware parser/dispatcher/timebase/safety parity).",
    "- Current repository implements Phase-3 closure primarily via tests/harnesses and fixtures; live-runtime and GUI verification remain explicitly unverified in Phase 3 artifact reports.",
    "- Blocking artifact integrity issue:",
    "- `docs/artifacts/phase3/phase3_evidence_bundle.json` cannot be parsed as JSON.",
)


def test_p3_gk_010_phase3_gatekeeper_implementation_status_contract_is_explicit() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## IMPLEMENTATION STATUS" in report
    assert "## TEST SUITE HEALTH" in report

    status_section = report.split("## IMPLEMENTATION STATUS", maxsplit=1)[1].split(
        "## TEST SUITE HEALTH", maxsplit=1
    )[0]

    for line in REQUIRED_STATUS_LINES:
        assert line in status_section
