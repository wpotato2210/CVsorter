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

## Phase 3 — Canonical safe tasks (test/harness/evidence only)

| ID | Module scope | Description | Expected artifact | Verification test |
|---|---|---|---|---|
| T3-001 | tests, protocol, serial_interface | Finalize deterministic protocol command/ACK vector corpus for HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE; require canonical field ordering and byte-stable fixture snapshots. | `tests/fixtures/protocol_vectors_t3_001.json` and companion expected-response fixture | `pytest tests/ -k "protocol and vector and t3_001"` |
| T3-002 | tests, bench, runtime | Build fixed-seed timing jitter corpus and envelope assertions covering pass/edge/fail windows for scheduler timing behavior without changing scheduling semantics. | `tests/fixtures/timing_jitter_t3_002.json` + deterministic envelope report snapshot | `pytest tests/ -k "timing and jitter and t3_002"` |
| T3-003 | tests, bench, serial_interface | Promote trigger-correlation checks from placeholder to strict deterministic test: accepted schedule command must map to exactly one terminal status record in trace artifacts. | `tests/test_phase3_t3_003_trigger_correlation.py` + reconciliation fixture | `pytest tests/ -k "t3_003 and trigger and correlation"` |
| T3-004 | tools, tests | Harden informational HIL gate into deterministic repeatability gate logic in tooling/tests (no contract changes): same fixed run set must produce stable verdicts and variance bounds. | `tools/hil_determinism_gate.py` (or updated gate tool) + gate config fixture | `pytest tests/ -k "t3_004 and hil and determinism"` |
| T3-005 | tests, bench, runtime | Add bench-vs-live parity trace suite for identical fixtures, asserting matching decision, reason, mode, queue, and scheduler-state transitions. | `tests/test_phase3_t3_005_bench_live_parity.py` + parity trace fixtures | `pytest tests/ -k "t3_005 and parity"` |
| T3-006 | tools, scripts, tests | Add deterministic evidence bundler that collects protocol parity, timing envelope, trigger correlation, and HIL-repeatability outputs into one phase sign-off package. | `tools/phase3_evidence_bundle.py` output directory in `docs/artifacts/phase3/` | `python tools/phase3_evidence_bundle.py --verify-only` |

### Phase 3 minimum completion path
1. T3-001 (protocol vectors)
2. T3-002 (timing envelopes)
3. T3-003 (trigger reconciliation)
4. T3-005 (bench/live parity)
5. T3-004 (deterministic HIL gate)
6. T3-006 (evidence bundle + closure report)

---

## Phase 4 — Canonical safe tasks (risk containment execution)

| ID | Module scope | Description | Expected artifact | Verification test |
|---|---|---|---|---|
| T4-001 | tests, protocol, serial_interface | Expand malformed-frame and NACK-mapping deterministic conformance suite aligned with risk row 3.1 failure detection. | `tests/test_phase4_t4_001_protocol_malformed_frames.py` | `pytest tests/ -k "t4_001 and protocol and malformed"` |
| T4-002 | tests, scheduler, bench | Add SAFE-mode invariant stress tests proving no actuation path when SAFE is active and queue ordering remains deterministic. | `tests/test_phase4_t4_002_safe_mode_invariants.py` | `pytest tests/ -k "t4_002 and safe"` |
| T4-003 | tests, bench, runtime | Implement differential trace comparator for fault-injected scenarios; assert zero divergence across bench/live state-transition traces. | `tests/test_phase4_t4_003_trace_comparator.py` + fault scenario fixtures | `pytest tests/ -k "t4_003 and differential and trace"` |
| T4-004 | tests, bench | Build timing-drift regression harness with fixed jitter injection and envelope assertions mapped to risk row 3.4. | `tests/test_phase4_t4_004_timing_drift_regression.py` | `pytest tests/ -k "t4_004 and timing and drift"` |
| T4-005 | scripts, tools, tests | Add rollback-drill automation that verifies each documented rollback strategy can be executed and validated in dry-run mode. | `scripts/phase4_rollback_drills.py` + generated drill log | `python scripts/phase4_rollback_drills.py --dry-run --verify` |
| T4-006 | tools, tests | Add repeated-run flake classifier for HIL/regression suites to separate deterministic failures from infrastructure noise. | `tools/phase4_flake_classifier.py` + classifier summary artifact | `python tools/phase4_flake_classifier.py --input docs/artifacts/phase4 --verify` |

### Phase 4 minimum completion path
1. T4-001 (protocol failure detection)
2. T4-002 (SAFE invariants)
3. T4-004 (timing drift harness)
4. T4-003 (bench/live divergence containment)
5. T4-005 (rollback drill evidence)
6. T4-006 (stability/flake evidence)

---

## Phase 5 — Planning-only safe backlog

| ID | Module scope | Description | Expected artifact | Verification test |
|---|---|---|---|---|
| T5-001 | docs, tools | Define Phase 5 release-evidence matrix template (required artifacts, thresholds, ownership, review cadence). | `docs/phase5_release_evidence_matrix.md` | `pytest tests/ -k "phase5 and evidence and template"` (if template validation tests exist) |
| T5-002 | docs, scripts | Draft deterministic operations readiness checklist generator plan (inputs/outputs only, no runtime behavior changes). | `docs/phase5_ops_readiness_plan.md` | `python scripts/phase5_readiness_plan_check.py --verify` (if added) |
| T5-003 | docs, tests | Define long-run parity campaign specification (session counts, fixed seeds, acceptance metrics, storage path). | `docs/phase5_long_run_campaign_spec.md` | `pytest tests/ -k "phase5 and campaign and spec"` (if spec tests exist) |

### Phase 5 minimum completion path
1. T5-001
2. T5-002
3. T5-003

---

## Missing-task additions introduced in this update

The following missing tasks were added to make Phase 3/4 completion paths minimally complete under safe constraints:
- Phase 3: **T3-005**, **T3-006**
- Phase 4: **T4-005**, **T4-006**
- Phase 5 planning normalization: **T5-001**, **T5-002**, **T5-003**

These additions close gaps between existing harness-level tasks and full phase-close evidence requirements.

---

## Phase completion checklist

### Phase 3 completion checklist
- [ ] T3-001 through T3-006 completed.
- [ ] Protocol vector replay results are deterministic across repeated runs.
- [ ] Trigger correlation is 1:1 for accepted commands and terminal status records.
- [ ] Timing envelope regressions are green at boundary cases.
- [ ] Bench/live parity traces show zero divergence for fixed fixtures.
- [ ] Deterministic HIL gate passes configured repeatability threshold.
- [ ] Phase 3 evidence bundle generated and archived.

### Phase 4 completion checklist
- [ ] T4-001 through T4-006 completed.
- [ ] All roadmap risk rows have a mapped test harness and pass result.
- [ ] Rollback drills validated in deterministic dry-run mode.
- [ ] Timing drift and SAFE-mode invariant suites are stable across repeated runs.
- [ ] Flake classifier report shows no unresolved release-blocking ambiguity.

### Phase 5 completion checklist (planning-only)
- [ ] T5-001 through T5-003 completed.
- [ ] Evidence matrix approved for release governance.
- [ ] Operations readiness plan reviewed and baselined.
- [ ] Long-run campaign spec approved for execution window.

---

## Execution commands to record for this board

1. `pytest tests/`
2. `pytest bench/`
3. `run_tests.bat` (where supported)
4. `pytest --cov=src/coloursorter --cov-report=xml`

If blocked, record exact blocker and continue remaining checks.
