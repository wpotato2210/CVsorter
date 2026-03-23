from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PLAN_PATH = Path("docs/phase5_ops_readiness_plan.md")
SCRIPT_PATH = Path("scripts/phase5_readiness_plan_check.py")


def _read_plan() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def test_t5_002_plan_exists_and_declares_planning_only_status() -> None:
    plan = _read_plan()

    assert PLAN_PATH.exists()
    assert "# Phase 5 Operations Readiness Checklist Generator Plan (T5-002)" in plan
    assert "Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes)." in plan


def test_t5_002_plan_declares_required_constants_io_and_outputs() -> None:
    plan = _read_plan()

    required_rows = (
        "| `plan_id` | `P5-OPS-READY-001` | Stable operations-readiness plan identifier. |",
        "| `checklist_id_prefix` | `P5-OPS-CHK` | Stable prefix for generated checklist identifiers. |",
        "| `input_manifest` | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | Canonical manifest describing deterministic checklist inputs. |",
        "| `output_root` | `docs/artifacts/phase5/ops_readiness/` | Canonical checklist output root. |",
        "- `release_candidate`: string identifier (for example `RC-001`)",
        "- `checklist_markdown_path`: generated checklist markdown path",
        "- `summary_json_path`: deterministic checklist summary path",
        "- per release candidate",
    )
    for row in required_rows:
        assert row in plan


def test_t5_002_plan_freezes_canonical_inputs_outputs_and_checklist_rows() -> None:
    plan = _read_plan()

    expected_entries = (
        "| `P5-OPS-IN-001` | release_evidence_matrix | `docs/phase5_release_evidence_matrix.md` | `matrix_id`, canonical evidence rows, review cadence |",
        "| `P5-OPS-IN-005` | release_candidate_manifest | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | release candidate id, owners, planned review window |",
        "| `P5-OPS-OUT-004` | manifest_copy | `docs/artifacts/phase5/ops_readiness/<release_candidate>/input_manifest.json` | Exact copy of canonical input manifest used to generate the checklist. |",
        "| `P5-OPS-CHK-001` | release_evidence_complete | `P5-OPS-IN-001` | All six release evidence rows assigned and review cadence populated. | `not_started` |",
        "| `P5-OPS-CHK-006` | approval_path_defined | `P5-OPS-IN-001`, `P5-OPS-IN-005` | Required approvers, blockers, and sign-off path recorded. | `not_started` |",
    )
    for entry in expected_entries:
        assert entry in plan

    input_rows = [line for line in plan.splitlines() if line.startswith("| `P5-OPS-IN-")]
    output_rows = [line for line in plan.splitlines() if line.startswith("| `P5-OPS-OUT-")]
    checklist_rows = [line for line in plan.splitlines() if line.startswith("| `P5-OPS-CHK-")]

    assert len(input_rows) == 5
    assert len(output_rows) == 4
    assert len(checklist_rows) == 6


def test_t5_002_plan_declares_deterministic_generation_rules_and_storage_layout() -> None:
    plan = _read_plan()

    required_rules = (
        "1. Read canonical inputs in the fixed order `P5-OPS-IN-001` through `P5-OPS-IN-005`.",
        "2. Emit checklist rows in ascending checklist-id order without sorting by any runtime-derived value.",
        "3. Copy verification command text exactly from the authoritative planning documents; do not rewrite commands.",
        "5. Reject generation if any required input group or canonical checklist row is missing.",
        "6. Reject generation if output paths escape `docs/artifacts/phase5/ops_readiness/`.",
        "docs/artifacts/phase5/ops_readiness/",
        "ops_readiness_checklist.md",
        "ops_readiness_checklist.json",
        "ops_readiness_summary.json",
    )
    for rule in required_rules:
        assert rule in plan


def test_t5_002_verifier_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--verify"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"verified_plan={PLAN_PATH}" in result.stdout
    assert "canonical_inputs=5" in result.stdout
    assert "canonical_outputs=4" in result.stdout
    assert "canonical_checklist_rows=6" in result.stdout
