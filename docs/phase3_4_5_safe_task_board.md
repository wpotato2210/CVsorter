# Phase 3/4/5 Canonical Safe Task Board

## Purpose

This board defines the **minimum complete safe path** to close Phase 3 and Phase 4 using only:
- tests
- harnesses
- validation gates
- parity and determinism evidence

It intentionally excludes runtime/protocol/schema contract mutation.

## Safety constraints (hard)

- Do not modify runtime I/O contracts.
- Do not modify protocol schemas or OpenSpec contract files.
- Do not add new production semantics.
- Focus on deterministic evidence and gate hardening.

## Phase definitions consolidated from planning docs

| Phase | Consolidated definition | Source anchors |
|---|---|---|
| Phase 3 | Deterministic closeout of see->decide->trigger->verify through protocol parity, trigger reconciliation, timebase envelope checks, safety parity, and deterministic HIL gating. | `deterministic_execution_roadmap.md`, `phase3_start_assessment.md`, `phase3_feature_discovery.md` |
| Phase 4 | Risk containment for Phase 3 failure modes using detection harnesses, rollback drills, and repeatable regression monitors. | `deterministic_execution_roadmap.md` |
| Phase 5 | Planning-only hardening backlog and release-evidence operations package; no active runtime scope in current roadmap. | `phase3_4_5_safe_task_board.md` (previous), `phase3_feature_discovery.md` |

---

## Consolidated execution source

The actionable Phase 3/4/5 safe-path tasks were merged into the single canonical task list at [`TASKS.md`](../TASKS.md).

This file remains the phase-definition and safety-constraint context document. It is no longer the authoritative location for executable task tracking or completion checklists.
