# Bench Controller Transition Audit (GUI controller regressions)

## Scope and method

Audited call paths requested in:

- `tests/test_bench_controller.py`
- `tests/test_bench_controller_gui.py`
- `gui/bench_app/controller.py`

The audit traces each failing-path expectation from test invocation through transition request, state-machine trigger emission, entered callbacks, runtime state publication, overlay emission, and UI signal wiring.

## Full call-chain trace

### Illegal replay→live test path

1. Tests call `controller._transition_to(ControllerState.REPLAY_RUNNING, ...)`, then `controller._transition_to(ControllerState.LIVE_RUNNING, ...)` while replay is active.
2. `BenchAppController._transition_to` delegates to `_request_transition`.
3. `_request_transition` calls `self._state_machine.request(state)`.
4. `BenchControllerStateMachine.request` currently checks `_is_allowed_transition(self._current_state, state)` **before** emitting trigger signals.
5. For replay→live, `_is_allowed_transition` returns `False`.
6. Because of that pre-gate, `start_live.emit()` is never called; request returns `False` immediately.
7. `_request_transition` clears pending overlay, emits runtime state, and returns `False`.

### State-enter side effects path

When a transition is accepted and entered callback runs:

1. `BenchControllerStateMachine` emits `entered` from Qt state `entered` handlers.
2. `BenchAppController._on_controller_state_entered` handles `entered` and is the sole mutator of `runtime_state.controller_state`.
3. This method starts/stops `_cycle_timer`, updates buttons, conditionally emits pending overlay text, and emits queue/fault runtime state.

This centralization behavior matches the tests’ design intent.

### Overlay behavior path

- `_request_transition` records overlay text as pending and binds it to `_pending_overlay_state`.
- `_on_controller_state_entered` only emits overlay when entered state equals `_pending_overlay_state`.
- Rejected transitions clear pending overlay and do not emit new overlay text.

This overlay gating is structurally correct, but it depends on transition outcome timing and trigger emission semantics.

## Confirmed divergence from test expectations

### 1) Trigger emission semantics drifted

Tests assert `start_live` trigger should fire even when replay→live transition is illegal, while no `entered` callback should occur. Current implementation blocks trigger emission via `_is_allowed_transition` pre-check, so the trigger counter remains zero.

This is the largest direct mismatch with current tests and matches the reported harness failures around `_transition_to()`.

### 2) Dual transition-policy sources create drift risk

Transition legality is encoded twice:

- Qt state graph (`addTransition(...)`), and
- `_is_allowed_transition(...)` static map.

These can diverge independently and produce hard-to-debug behavior where request() says “rejected” before Qt graph evaluates the trigger.

### 3) Rejection path still emits runtime state snapshot

On rejected transitions, `_request_transition` calls `_emit_runtime_state()` even though no entered callback occurs. Tests currently account for this (queue-state event count increments by one), but this introduces observable side effects whose ordering can vary across environments if additional queued Qt events exist.

### 4) SAFE guardrail pre-check bypasses state-machine trigger path

For SAFE fault-state restrictions (`SAFE` -> non-`IDLE`), `_request_transition` returns before calling `state_machine.request`. This is protocol-correct for safety, but it differs from generic transition rejection path behavior and may produce inconsistent trigger/telemetry behavior between “policy-rejected” and “graph-rejected” cases.

## Repair tasks (do not modify tests)

### Task 1 — Align trigger emission with test contract on rejected graph transitions

- **Root cause:** `BenchControllerStateMachine.request` prevents trigger signal emission on illegal transitions by pre-checking `_is_allowed_transition`.
- **Files:** `gui/bench_app/controller.py` (state machine `request`, possibly `_is_allowed_transition`).
- **Minimal change:** Emit the mapped trigger for target state when `state != _current_state`; rely on Qt state graph to accept/reject transition, then let `_request_transition` detect completion via entered callback. Keep return `False` when no state entry occurs.
- **Risk:** Medium (changes transition semantics observable by signal listeners).
- **Tests expected to pass:** illegal replay→live consistency tests in both test modules, plus trigger count assertions.

### Task 2 — Keep `_on_controller_state_entered` as sole state mutator and side-effect authority

- **Root cause:** Regressions historically came from pre-assigning controller state before transition completion; this must stay centralized.
- **Files:** `gui/bench_app/controller.py` (`_transition_to`, `_request_transition`, `_on_controller_state_entered`).
- **Minimal change:** Preserve current design where only `_on_controller_state_entered` sets runtime state/timer/buttons; add an inline invariant comment + optional assertion in transition request path to prevent future pre-assignment regressions.
- **Risk:** Low.
- **Tests expected to pass:** preassignment guard tests and overlay-order tests.

### Task 3 — Normalize rejected-transition behavior for overlay and status emissions

- **Root cause:** Rejected transitions currently emit runtime state snapshots in `_request_transition`; this is relied on by tests but can cause environment-sensitive ordering if other queued events are pending.
- **Files:** `gui/bench_app/controller.py` (`_request_transition`).
- **Minimal change:** Keep `_emit_runtime_state()` for deterministic UI refresh, but make rejection branch explicit and identical for all non-entered outcomes (graph-rejected and timeout-not-entered), including consistent clearing of pending overlay state.
- **Risk:** Low.
- **Tests expected to pass:** illegal transition consistency tests, no-overlay-on-reject assertions.

### Task 4 — Unify SAFE guardrail rejection telemetry with generic rejection path

- **Root cause:** SAFE pre-guard returns before state machine request; this can skip trigger/diagnostic parity and create behavior drift relative to other rejected transitions.
- **Files:** `gui/bench_app/controller.py` (`_request_transition`).
- **Minimal change:** Keep protocol safety rule intact, but route SAFE policy rejection through a shared helper that applies the same overlay clearing and runtime-state emission semantics as other rejections.
- **Risk:** Medium (touches safety-path control flow; must preserve SAFE guarantees).
- **Tests expected to pass:** SAFE overlay and recovery tests, illegal transition consistency tests.

### Task 5 — Add focused controller tests for trigger-vs-enter separation

- **Root cause:** Lack of explicit tests for “trigger emitted but no entered callback” allowed drift.
- **Files:** `tests/test_bench_controller.py`, `tests/test_bench_controller_gui.py`.
- **Minimal change:** Add/adjust tests asserting replay→live illegal request produces: trigger emission count increment, no entered-state event, unchanged runtime state, unchanged timer/buttons, and no overlay emission.
- **Risk:** Low.
- **Tests expected to pass:** both transition-gate tests and regression coverage for future refactors.

### Task 6 — Add deterministic Qt event-drain helper for transition completion checks

- **Root cause:** `_request_transition` loops `processEvents()` 3x inline; duplicated timing assumptions increase flake risk across platforms.
- **Files:** `gui/bench_app/controller.py`.
- **Minimal change:** Extract a tiny private helper (`_drain_events_until_state` or equivalent) with fixed iteration budget and one deterministic contract used by `_request_transition`.
- **Risk:** Low/Medium (timing-sensitive path).
- **Tests expected to pass:** all existing GUI transition and overlay-order tests; reduced Windows timing variance.

## Conclusion

Primary root cause is transition-trigger gating in `BenchControllerStateMachine.request` that rejects illegal transitions before emitting trigger signals, conflicting with current test expectations that distinguish trigger emission from actual entered-state transitions. Secondary issues are consistency and determinism concerns in rejection-path side effects.
