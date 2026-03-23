#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PLAN_PATH = Path("docs/phase5_ops_readiness_plan.md")

REQUIRED_SNIPPETS = (
    "# Phase 5 Operations Readiness Checklist Generator Plan (T5-002)",
    "Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes).",
    "| `plan_id` | `P5-OPS-READY-001` | Stable operations-readiness plan identifier. |",
    "| `input_manifest` | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | Canonical manifest describing deterministic checklist inputs. |",
    "| `P5-OPS-IN-005` | release_candidate_manifest | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | release candidate id, owners, planned review window |",
    "| `P5-OPS-OUT-002` | checklist_json | `docs/artifacts/phase5/ops_readiness/<release_candidate>/ops_readiness_checklist.json` | Machine-readable checklist rows in deterministic order. |",
    "| `P5-OPS-CHK-006` | approval_path_defined | `P5-OPS-IN-001`, `P5-OPS-IN-005` | Required approvers, blockers, and sign-off path recorded. | `not_started` |",
    "1. Read canonical inputs in the fixed order `P5-OPS-IN-001` through `P5-OPS-IN-005`.",
    "3. Copy verification command text exactly from the authoritative planning documents; do not rewrite commands.",
    "docs/artifacts/phase5/ops_readiness/",
)


def _verify_plan_text(plan_text: str) -> list[str]:
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in plan_text]
    plan_lines = plan_text.splitlines()
    if len([line for line in plan_lines if line.startswith("| `P5-OPS-CHK-")]) != 6:
        missing.append("expected exactly 6 canonical checklist rows")
    if len([line for line in plan_lines if line.startswith("| `P5-OPS-IN-")]) != 5:
        missing.append("expected exactly 5 canonical input groups")
    if len([line for line in plan_lines if line.startswith("| `P5-OPS-OUT-")]) != 4:
        missing.append("expected exactly 4 canonical generated outputs")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Phase 5 ops readiness plan contract")
    parser.add_argument("--verify", action="store_true", help="verify the plan contract")
    args = parser.parse_args()

    if not args.verify:
        parser.error("the following arguments are required: --verify")

    plan_text = PLAN_PATH.read_text(encoding="utf-8")
    missing = _verify_plan_text(plan_text)
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1

    print(f"verified_plan={PLAN_PATH}")
    print("canonical_inputs=5")
    print("canonical_outputs=4")
    print("canonical_checklist_rows=6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
