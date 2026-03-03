# OpenSpec v3 Firmware State Machine Export

## States
- `BOOT`: power-on initialization.
- `SYNCING`: after valid `HELLO`, before first `HEARTBEAT`.
- `READY`: protocol synchronized and heartbeat alive.
- `DEGRADED`: heartbeat timeout exceeded.
- `SAFE_HALT`: brownout or watchdog fault latched.

## Transition table
| From | Event | To | OpenSpec command/condition |
|---|---|---|---|
| BOOT | HELLO(version=3.1) | SYNCING | `HELLO` accepted |
| SYNCING | HEARTBEAT | READY | `HEARTBEAT` accepted |
| READY | heartbeat timeout | DEGRADED | timeout > budget |
| DEGRADED | HEARTBEAT | READY | link restored |
| * | watchdog expiry | SAFE_HALT | watchdog module fault |
| * | brownout trip | SAFE_HALT | supply below threshold |
| SAFE_HALT | RESET_QUEUE + SET_MODE(MANUAL) | SYNCING | controlled recovery |

## Timing budgets
- Main scheduler tick: **1 ms**.
- Heartbeat supervision window: **500 ms**.
- Fault latch propagation (watchdog/brownout): **< 5 ms**.
