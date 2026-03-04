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

`recover_to_auto` is therefore only valid when controller state is `IDLE` and the mode policy allows the transition (canonical SAFE path remains `SAFE -> MANUAL -> AUTO`).

1. `SET_MODE` is the only command that changes controller mode.
2. Mode authority is host-owned. GUI recovery actions are GUI-assisted command issuers only.
3. Any accepted mode change clears queued scheduler entries before applying target mode.
4. Explicit SAFE entry (`SET_MODE|SAFE`) always clears queue and transitions scheduler state to `IDLE`.
5. `SAFE -> AUTO` direct transition is invalid and returns `NACK|5|INVALID_MODE_TRANSITION`.
6. Canonical SAFE recovery path is `SAFE -> MANUAL -> AUTO`.
7. `RESET_QUEUE` is allowed in any mode and only affects queue/scheduler state (`IDLE` when empty).


## Queue-depth authority
- Normative owner: MCU/host ACK metadata (`ACK|...|queue_depth=<n>|...`) and `GET_STATE` snapshots are the only authoritative queue-depth truth.
- Bench/runtime caches (for example transport/UI mirrors) are derived-only and may lag, but MUST NOT override newer ACK/`GET_STATE` values or trigger corrective resets by themselves.
- Queue reset decisions are driven by mode/scheduler mismatches and explicit reset commands, not cache drift.

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
- `Home` in SAFE is constrained to `recover_safe_to_manual()` only; it does not attempt AUTO promotion.
- AUTO recovery controls are exposed only for `IDLE` states so replay/live runs cannot bypass transition guards.
- Validation references: `tests/test_bench_controller.py` and `tests/test_protocol_compliance_v3.py`.
