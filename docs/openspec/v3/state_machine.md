# OpenSpec v3 State Machine

## Controller modes
- `AUTO`
- `MANUAL`
- `SAFE`

## Transition rules
1. `SET_MODE` is the only command that changes controller mode.
2. Any mode change clears queued scheduler entries before applying target mode.
3. Explicit SAFE entry (`SET_MODE|SAFE`) always clears queue.
4. `SAFE -> AUTO` direct transition is invalid and returns `NACK|5|INVALID_MODE_TRANSITION`.
5. Recovery path from SAFE is `SAFE -> MANUAL -> AUTO`.

## Scheduler states
- `IDLE`: queue is empty.
- `ACTIVE`: queue has one or more pending entries.

## Fault transitions
- Missing pulses: bench remains at previous trigger timestamp and may enter SAFE via transport NACK.
- Zero belt speed: same as missing pulse behavior.
- Watchdog timeout: transport fault state transitions to `WATCHDOG`.
- Explicit SAFE command: immediate `mode=SAFE`, queue cleared, `scheduler_state=IDLE`.


## GUI/operator recovery
- SAFE can be cleared directly to AUTO in operator flow.
- SAFE recovery can also follow `SAFE -> MANUAL -> AUTO` in operator flow.
- Validation reference: `tests/test_bench_controller.py`.
