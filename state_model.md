# state_model.md

## Purpose
Define authoritative runtime states and transitions for mode control, scheduler lifecycle, queue depth, and trigger execution across CV and protocol boundaries.

## Inputs / Outputs
- **Inputs**
  - Protocol commands (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`).
  - Frame-derived scheduling decisions from CV pipeline.
  - Transport feedback (ACK/NACK/timeout).
- **Outputs**
  - Validated state transitions and canonical state snapshots.
  - Scheduler dispatch outcomes and queue depth telemetry.

## States
- `mode`: `AUTO | MANUAL | SAFE`.
- `scheduler_state`: `IDLE | ACTIVE`.
- `queue_depth`: integer in `0..8`.
- `host_state`: `READY | BUSY`.
- `trigger_state` (conceptual): `queued | sent | acked | failed`.

## Dependencies
- `protocol.md` transition policy and ACK/NACK contract.
- `threading_model.md` atomic transition and snapshot consistency rules.
- Scheduler queue implementation.
- Bench CLI/GUI state visualization components.

## Key Behaviors / Invariants
- Allowed mode transitions: `AUTO -> {AUTO, MANUAL, SAFE}`, `MANUAL -> {AUTO, MANUAL, SAFE}`, `SAFE -> {SAFE, MANUAL}`.
- Effective mode changes clear queue and force `scheduler_state=IDLE`.
- `SCHED` accepted only when argument bounds pass and queue has capacity.
- Any non-empty queue implies `scheduler_state=ACTIVE` until drained/reset.
- `GET_STATE` returns a coherent snapshot (mode, queue depth, scheduler state, queue_cleared).

## Cross-layer Dependency Notes
- `constraints.md` is source of truth for accepted `lane` and `trigger_mm` ranges.
- `error_model.md` consumes invalid transitions/admissions to emit canonical NACKs.
- `security_model.md` may force state restrictions during suspicious traffic conditions.

## Performance / Concurrency Notes
- Non-atomic reads can expose inconsistent state snapshots under concurrent queue mutation.
- High-frequency `GET_STATE` polling can starve command processing in single-threaded loops.

## Open Questions (requires input)
- Whether mode transitions can occur asynchronously mid-dispatch or only at queue-empty boundaries.
- Whether intermediate scheduler states (for example `DISPATCHING`, `AWAITING_ACK`) should be explicit.
- SAFE-mode behavior for partially processed frames and already-enqueued triggers under active errors.

## Conflicts / Missing Links
- No explicit state machine diagram file currently accompanies this textual model.
