# Phase 3/4 Safe Task Board (Beginner-Friendly)

## Scope and safety boundary

This board is intentionally limited to **safe-now** work while overlap guardrails are active:

- docs/design updates
- non-gating test or harness scaffolding
- parity and determinism checks that do not change protocol contracts

Do **not** change production protocol/schema/runtime semantics in this board.

## Phase status snapshot

| Phase | Current status | Safe-now interpretation |
|---|---|---|
| Phase 3 | Defined in deterministic roadmap | Work on harnesses and test artifacts that prepare 3.1/3.4/3.6 without production contract mutation |
| Phase 4 | Defined as risk containment matrix | Implement and automate the listed detection harnesses and rollback drills |
| Phase 5 | Not defined in active roadmap file | Planning-only backlog drafting (no runtime or contract changes) |

## Task queue (safe now)

| ID | Module focus | Task | Output artifact | Test hint |
|---|---|---|---|---|
| T3-001 | protocol, serial_interface, bench | Create deterministic command/ACK vector pack for HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE paths | `tests/fixtures/protocol_vectors_*.json` + parser/conformance tests | Add strict byte/token assertions and stable field ordering |
| T3-002 | scheduler, deploy, bench | Create fixed-seed timing-jitter replay corpus with expected execution envelopes | `tests/fixtures/timing_jitter_*.json` + timing envelope tests | Assert exact pass/fail boundary around envelope edges |
| T3-003 | protocol, bench, deploy | Draft trigger-correlation test design (accepted command -> terminal status mapping) | `docs/artifacts/*` design note + placeholder tests | Keep tests informational and marked as non-release gating |
| T3-004 | tools, tests, bench | Scaffold deterministic HIL gate in informational mode only | `tools/*hil*` check + `tests/test_hil_*` skeleton | Validate deterministic rerun behavior with fixed seeds |
| T4-001 | protocol, serial_interface | Add malformed-frame and wrong-NACK mapping tests | New/extended protocol fuzz/conformance tests | Assert deterministic NACK reason and parser rejection path |
| T4-002 | scheduler | Add SAFE-mode invariant tests to ensure no actuation in SAFE | Scheduler/dispatch invariants in tests | Include queue ordering assertions under stress fixtures |
| T4-003 | bench, runtime, config | Add bench/live differential trace comparator suite | `tests/test_*parity*.py` trace comparisons | Compare decision, rejection reason, mode, scheduler state fields |
| T4-004 | bench, runtime | Add timing drift regression harness with injected transport jitter | Replay+jitter harness tests | Keep deterministic seed and fixed expected windows |
| T5-PLAN-001 | OpenSpec artifacts, config, GUI | Draft proposed Phase 5 backlog template (ops hardening, UX diagnostics, release evidence) | Planning doc only | No executable/runtime changes allowed until approved |

## Beginner implementation slices (first 3 PRs)

### PR-1: Protocol vectors + parser determinism
- Add fixtures and tests only.
- Do not modify protocol docs/contracts.
- Target outcomes:
  - stable parse/serialize behavior
  - explicit malformed frame rejection
  - deterministic ACK/NACK mapping

### PR-2: Timing jitter corpus + envelope tests
- Add fixed-seed replay fixtures.
- Add boundary tests (inside envelope, edge, outside).
- Keep transport semantics unchanged.

### PR-3: Bench/live parity trace checker
- Add deterministic event traces and comparator helpers.
- Verify identical behavior for same thresholds/fault context.
- Keep in non-gating or informational mode until sign-off.

## PySide6 signal-slot wiring checklist (GUI safety)

Use this checklist when touching Qt bench GUI paths:

1. Emit controller state transitions via explicit Qt `Signal`s only.
2. Keep UI mutation in slots/main thread (`set_queue_state`, `set_fault_state`, `append_log_entry`).
3. Never bypass state machine transitions with direct widget state hacks.
4. Ensure mode labels and queue/scheduler status derive from the same runtime snapshot.
5. Add GUI parity tests for mode/fault transitions and status-bar consistency.

## Mismatch watchlist and safe mitigations

| Risk type | Example mismatch | Safe mitigation now |
|---|---|---|
| Protocol vs transport | Token accepted in bench but rejected in serial parser | Add shared conformance vectors and run both paths against same fixtures |
| Bench vs live | Different rejection reason for same threshold input | Add differential trace tests with fixed input and exact expected reasons |
| GUI vs runtime | GUI shows RUNNING while runtime is SAFE/FAULTED | Bind labels/status only from controller state machine snapshots |
| Scheduler vs deploy | Schedule output accepted with stale/faulted frame context | Add boundary tests asserting fault precedence before schedule emit |
| Calibration vs preprocess | Channel/geometry assumptions diverge across modules | Add explicit fixture tests for accepted/rejected shape/channel/geometry cases |

## Closure checks for this board

When executing tasks from this board, run and record:

1. `pytest tests/`
2. `pytest bench/`
3. `run_tests.bat` (where environment supports firmware tests)
4. `pytest --cov=src/coloursorter --cov-report=xml` when coverage evidence is requested

If a command is blocked by environment/tooling, log exact blocker and continue with remaining checks.
