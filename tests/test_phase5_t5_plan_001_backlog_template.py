from __future__ import annotations

from pathlib import Path

SPEC_PATH = Path("docs/phase5_backlog_template.md")


def _spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def test_phase5_backlog_template_declares_planning_only_scope_and_guardrails() -> None:
    spec = _spec_text()

    assert "# Phase 5 Backlog Template (T5-PLAN-001)" in spec
    assert "Status: Draft (planning only; no runtime/protocol/contract changes)." in spec
    assert "This template is intentionally non-executable and preserves current frozen contracts." in spec

    for required in (
        "- No edits to protocol contracts, timing guarantees, or architecture artifacts.",
        "- No runtime semantic changes from this planning document.",
        '- Any proposed item that would alter frozen contracts must be routed as an explicit contract-change request.',
    ):
        assert required in spec


def test_phase5_backlog_template_defines_deterministic_priority_formula_and_sort_order() -> None:
    spec = _spec_text()

    for required in (
        "Use deterministic scoring per item:",
        "- Impact: 1-5",
        "- Risk reduction: 1-5",
        "- Effort: 1-5",
        "- Priority score = `(Impact + Risk reduction) - Effort`",
        'Sort descending by `Priority score`, then ascending by `Item ID`.',
    ):
        assert required in spec


def test_phase5_backlog_template_requires_schema_categories_and_placeholder_rows() -> None:
    spec = _spec_text()

    for required in (
        "- Item ID: `T5-<area>-<nnn>`",
        "- Category: `ops_hardening | ux_diagnostics | release_evidence`",
        "- Acceptance evidence",
        "- Dependencies",
        "- Risks/rollback",
        "- Priority score inputs (Impact, Risk reduction, Effort)",
        "| T5-OPS-001 | ops_hardening | Add item | Add item | Add item | Add item | Add item | TBD | 0 | 0 | 0 | 0 | TBD |",
        "| T5-UX-001 | ux_diagnostics | Add item | Add item | Add item | Add item | Add item | TBD | 0 | 0 | 0 | 0 | TBD |",
        "| T5-REL-001 | release_evidence | Add item | Add item | Add item | Add item | Add item | TBD | 0 | 0 | 0 | 0 | TBD |",
    ):
        assert required in spec


def test_phase5_backlog_template_lists_execution_readiness_gates_and_review_checklist() -> None:
    spec = _spec_text()

    readiness_gates = [
        '1. Determinism impact assessed and documented.',
        '2. Protocol/interface impact classified as "none" or reviewed through formal contract-change request.',
        '3. Test evidence plan defined (host tests, bench tests, firmware checks as applicable).',
        '4. Rollback and safe-mode behavior documented.',
    ]
    for gate in readiness_gates:
        assert gate in spec

    review_checks = [
        '- [ ] Item is planning-only and does not mutate runtime behavior.',
        '- [ ] Module boundaries affected are explicit.',
        '- [ ] Evidence artifacts are concrete and reproducible.',
        '- [ ] Risks include timing and protocol compliance considerations.',
        '- [ ] Owner and milestone are assigned.',
    ]
    for checklist_item in review_checks:
        assert checklist_item in spec
