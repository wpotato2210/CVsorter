from __future__ import annotations

from pathlib import Path

SPEC_PATH = Path("docs/phase3_4_5_safe_task_board.md")


def _spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def test_phase5_section_is_planning_only_and_lists_canonical_tasks() -> None:
    spec = _spec_text()

    for required in (
        "## Phase 5 — Planning-only safe backlog",
        "| T5-001 | docs, tools | Define Phase 5 release-evidence matrix template (required artifacts, thresholds, ownership, review cadence). | `docs/phase5_release_evidence_matrix.md` | `pytest tests/ -k \"phase5 and evidence and template\"` (if template validation tests exist) |",
        "| T5-002 | docs, scripts | Draft deterministic operations readiness checklist generator plan (inputs/outputs only, no runtime behavior changes). | `docs/phase5_ops_readiness_plan.md` | `python scripts/phase5_readiness_plan_check.py --verify` (if added) |",
        "| T5-003 | docs, tests | Define long-run parity campaign specification (session counts, fixed seeds, acceptance metrics, storage path). | `docs/phase5_long_run_campaign_spec.md` | `pytest tests/ -k \"phase5 and campaign and spec\"` (if spec tests exist) |",
    ):
        assert required in spec


def test_phase5_completion_path_and_checklist_are_ordered_and_explicit() -> None:
    spec = _spec_text()

    completion_path = [
        "1. T5-001",
        "2. T5-002",
        "3. T5-003",
    ]
    for item in completion_path:
        assert item in spec

    checklist = [
        "### Phase 5 completion checklist (planning-only)",
        "- [ ] T5-001 through T5-003 completed.",
        "- [ ] Evidence matrix approved for release governance.",
        "- [ ] Operations readiness plan reviewed and baselined.",
        "- [ ] Long-run campaign spec approved for execution window.",
    ]
    for item in checklist:
        assert item in spec

    assert spec.index(completion_path[0]) < spec.index(completion_path[1]) < spec.index(completion_path[2])


def test_phase5_missing_task_additions_and_execution_commands_are_retained() -> None:
    spec = _spec_text()

    for required in (
        "- Phase 5 planning normalization: **T5-001**, **T5-002**, **T5-003**",
        "## Execution commands to record for this board",
        "1. `pytest tests/`",
        "2. `pytest bench/`",
        "3. `run_tests.bat` (where supported)",
        "4. `pytest --cov=src/coloursorter --cov-report=xml`",
        "If blocked, record exact blocker and continue remaining checks.",
    ):
        assert required in spec
