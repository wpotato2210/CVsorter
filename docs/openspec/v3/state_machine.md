# OpenSpec v3 State Machine

## Controller modes
- `AUTO`
- `MANUAL`
- `SAFE`

## Transition rules
### Mode transition contract (single source for host + GUI)

| From \ To | AUTO | MANUAL | SAFE |
| --- | --- | --- | --- |
| AUTO | ✅ allowed | ✅ allowed | ✅ allowed |
| MANUAL | ✅ allowed | ✅ allowed | ✅ allowed |
| SAFE | ❌ rejected (`NACK|5|INVALID_MODE_TRANSITION`) | ✅ allowed | ✅ allowed |

`recover_to_auto` is therefore only valid when controller mode is not `SAFE` (canonical path remains `SAFE -> MANUAL -> AUTO`).

1. `SET_MODE` is the only command that changes controller mode.
2. Mode authority is host-owned. GUI recovery actions are GUI-assisted command issuers only.
3. Any accepted mode change clears queued scheduler entries before applying target mode.
4. Explicit SAFE entry (`SET_MODE|SAFE`) always clears queue and transitions scheduler state to `IDLE`.
5. `SAFE -> AUTO` direct transition is invalid and returns `NACK|5|INVALID_MODE_TRANSITION`.
6. Canonical SAFE recovery path is `SAFE -> MANUAL -> AUTO`.
7. `RESET_QUEUE` is allowed in any mode and only affects queue/scheduler state (`IDLE` when empty).

## Scheduler states
- `IDLE`: queue is empty.
- `ACTIVE`: queue has one or more pending entries.

## Fault transitions
- Missing pulses: bench remains at previous trigger timestamp and may enter SAFE via transport NACK.
- Zero belt speed: same as missing pulse behavior.
- Watchdog timeout: transport fault state transitions to `WATCHDOG`.
- Explicit SAFE command: immediate `mode=SAFE`, queue cleared, `scheduler_state=IDLE`.


## GUI/operator recovery
- GUI must not locally mutate queue/mode to recover from SAFE.
- GUI recovery is command-driven and mirrors host rules:
  - `SAFE -> MANUAL`: allowed through `SET_MODE|MANUAL`.
  - `SAFE -> AUTO`: forbidden (`NACK|5|INVALID_MODE_TRANSITION`).
  - `MANUAL -> AUTO`: allowed through `SET_MODE|AUTO`.
- Validation references: `tests/test_bench_controller.py` and `tests/test_protocol_compliance_v3.py`.
