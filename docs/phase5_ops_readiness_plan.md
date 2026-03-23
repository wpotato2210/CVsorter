# Phase 5 Operations Readiness Checklist Generator Plan (T5-002)

Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes).

## Purpose

Define a deterministic plan for generating Phase 5 operations-readiness checklists.
This plan freezes checklist generator inputs, outputs, ordering, and storage contracts without changing runtime behavior.

## Guardrails

- No edits to runtime behavior, protocol framing, timing guarantees, or frozen architecture artifacts.
- Generator scope is limited to planning artifacts; it must not execute host, bench, firmware, or hardware commands.
- Checklist item ordering, identifier allocation, and output naming must remain deterministic.
- Any requested checklist field that would alter an existing contract must be raised as a separate contract-change request.

## Plan constants

| Variable | Value | Requirement |
|---|---|---|
| `plan_id` | `P5-OPS-READY-001` | Stable operations-readiness plan identifier. |
| `phase` | `Phase 5` | Planning-only operations readiness scope. |
| `checklist_id_prefix` | `P5-OPS-CHK` | Stable prefix for generated checklist identifiers. |
| `input_manifest` | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | Canonical manifest describing deterministic checklist inputs. |
| `output_root` | `docs/artifacts/phase5/ops_readiness/` | Canonical checklist output root. |
| `required_input_count` | 5 | Every generated checklist must reference all canonical input groups. |
| `required_output_count` | 4 | Every generated checklist must emit all canonical output artifacts. |
| `allowed_status_values` | `not_started | ready | blocked | approved` | Deterministic status set for checklist rows. |
| `max_missing_required_rows` | 0 | No required row may be absent from a generated checklist. |

## Generator I/O contract

Module: phase5_ops_readiness_generator

Inputs:
- `release_candidate`: string identifier (for example `RC-001`)
- `input_manifest_path`: path to canonical planning manifest JSON
- `release_evidence_matrix_path`: path to `docs/phase5_release_evidence_matrix.md`
- `campaign_spec_path`: path to `docs/phase5_long_run_campaign_spec.md`
- `backlog_template_path`: path to `docs/phase5_backlog_template.md`
- `safe_task_board_path`: path to `docs/phase3_4_5_safe_task_board.md`

Outputs:
- `checklist_markdown_path`: generated checklist markdown path
- `checklist_json_path`: generated checklist JSON path
- `summary_json_path`: deterministic checklist summary path
- `manifest_copy_path`: copied input manifest path stored with checklist artifacts

Side effects:
- Writes planning artifacts only under `docs/artifacts/phase5/ops_readiness/<release_candidate>/`
- Does not execute runtime, firmware, bench, or hardware actions
- Does not modify protocol, schema, OpenSpec, or source-code contracts

Dependencies:
- Local repository documentation listed above
- Canonical input manifest JSON
- Standard library file and JSON handling only

Update Rate:
- per release candidate

## Canonical input groups

| Input ID | Input group | Source | Required fields |
|---|---|---|---|
| `P5-OPS-IN-001` | release_evidence_matrix | `docs/phase5_release_evidence_matrix.md` | `matrix_id`, canonical evidence rows, review cadence |
| `P5-OPS-IN-002` | long_run_campaign_spec | `docs/phase5_long_run_campaign_spec.md` | `campaign_id`, session matrix, acceptance metrics |
| `P5-OPS-IN-003` | backlog_template | `docs/phase5_backlog_template.md` | item identifiers, ownership fields, status columns |
| `P5-OPS-IN-004` | safe_task_board | `docs/phase3_4_5_safe_task_board.md` | T5 ordering, dependencies, verification commands |
| `P5-OPS-IN-005` | release_candidate_manifest | `docs/artifacts/phase5/ops_readiness/input_manifest.json` | release candidate id, owners, planned review window |

## Canonical generated outputs

| Output ID | Output artifact | Path rule | Deterministic content |
|---|---|---|---|
| `P5-OPS-OUT-001` | checklist_markdown | `docs/artifacts/phase5/ops_readiness/<release_candidate>/ops_readiness_checklist.md` | Ordered checklist with frozen row set and reviewer assignments. |
| `P5-OPS-OUT-002` | checklist_json | `docs/artifacts/phase5/ops_readiness/<release_candidate>/ops_readiness_checklist.json` | Machine-readable checklist rows in deterministic order. |
| `P5-OPS-OUT-003` | summary_json | `docs/artifacts/phase5/ops_readiness/<release_candidate>/ops_readiness_summary.json` | Counts for ready, blocked, approved, and pending rows. |
| `P5-OPS-OUT-004` | manifest_copy | `docs/artifacts/phase5/ops_readiness/<release_candidate>/input_manifest.json` | Exact copy of canonical input manifest used to generate the checklist. |

## Canonical checklist rows

| Checklist ID | Readiness area | Input dependency | Required evidence | Default status |
|---|---|---|---|---|
| `P5-OPS-CHK-001` | release_evidence_complete | `P5-OPS-IN-001` | All six release evidence rows assigned and review cadence populated. | `not_started` |
| `P5-OPS-CHK-002` | parity_campaign_ready | `P5-OPS-IN-002` | Long-run campaign fixtures, seeds, and artifact root confirmed. | `not_started` |
| `P5-OPS-CHK-003` | backlog_alignment | `P5-OPS-IN-003` | Phase 5 backlog items mapped to owners and review windows. | `not_started` |
| `P5-OPS-CHK-004` | safe_task_order_locked | `P5-OPS-IN-004` | T5 task ordering and verification commands copied without modification. | `not_started` |
| `P5-OPS-CHK-005` | release_candidate_metadata | `P5-OPS-IN-005` | Release candidate id, operator, and review window captured in manifest. | `not_started` |
| `P5-OPS-CHK-006` | approval_path_defined | `P5-OPS-IN-001`, `P5-OPS-IN-005` | Required approvers, blockers, and sign-off path recorded. | `not_started` |

## Deterministic generation rules

1. Read canonical inputs in the fixed order `P5-OPS-IN-001` through `P5-OPS-IN-005`.
2. Emit checklist rows in ascending checklist-id order without sorting by any runtime-derived value.
3. Copy verification command text exactly from the authoritative planning documents; do not rewrite commands.
4. Preserve release candidate naming exactly as provided in the input manifest.
5. Reject generation if any required input group or canonical checklist row is missing.
6. Reject generation if output paths escape `docs/artifacts/phase5/ops_readiness/`.

## Suggested generated checklist fields

Each generated checklist row should declare the following fields:

- `checklist_id`
- `readiness_area`
- `input_dependencies`
- `required_evidence`
- `owner`
- `reviewers`
- `status`
- `blocking_issues`
- `last_updated_utc`
- `verification_command_reference`

## Storage layout

```text
docs/artifacts/phase5/ops_readiness/
  input_manifest.json
  RC-<nnn>/
    input_manifest.json
    ops_readiness_checklist.md
    ops_readiness_checklist.json
    ops_readiness_summary.json
```

## Non-goals

- No runtime code changes.
- No protocol or schema changes.
- No execution of readiness commands from this planning artifact.
- No nondeterministic checklist ordering, naming, or storage.
