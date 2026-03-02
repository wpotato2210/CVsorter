# protocol.md

## Scope
Reverse-engineered protocol reference from:
- `protocol/commands.json`
- `src/coloursorter/protocol/*`
- `src/coloursorter/serial_interface/*`

## Wire format
| Field | Value |
|---|---|
| Frame envelope | `<CMD|arg1|arg2>` |
| Encoding | ASCII |
| Delimiter | `|` |
| Start / end token | `<` / `>` |
| Argument constraints | No literal `<`, `>`, or `|` in payload |

## Commands
| Command | Args | Validation | Behavior |
|---|---|---|---|
| `SET_MODE` | `mode: AUTO|MANUAL|SAFE` | 1 arg, enum check, transition policy | Mode switch; clears queue if mode changes |
| `SCHED` | `lane: int`, `trigger_mm: float` | 2 args, lane `0..21`, trigger `0.0..2000.0`, queue-cap check | Enqueue trigger and set scheduler `ACTIVE` |
| `GET_STATE` | none | must have 0 args | Returns state snapshot |
| `RESET_QUEUE` | none | must have 0 args | Clears queue and sets scheduler `IDLE` |

## ACK/NACK contract
### ACK frame
`<ACK|mode|queue_depth|scheduler_state|queue_cleared>`

- `mode`: `AUTO|MANUAL|SAFE`
- `queue_depth`: decimal string
- `scheduler_state`: `IDLE|ACTIVE`
- `queue_cleared`: `true|false`

### NACK frame
`<NACK|code|detail>`

Canonical codes/details:
| Code | Detail |
|---|---|
| `1` | `UNKNOWN_COMMAND` |
| `2` | `ARG_COUNT_MISMATCH` |
| `3` | `ARG_RANGE_ERROR` |
| `4` | `ARG_TYPE_ERROR` |
| `5` | `INVALID_MODE_TRANSITION` |
| `6` | `QUEUE_FULL` |
| `7` | `BUSY` |
| `8` | `MALFORMED_FRAME` |

## Mode transition policy
Allowed transitions:
- `AUTO -> AUTO|MANUAL|SAFE`
- `MANUAL -> AUTO|MANUAL|SAFE`
- `SAFE -> SAFE|MANUAL`

Rejected transition example: `SAFE -> AUTO` (`NACK 5 INVALID_MODE_TRANSITION`).

## Queue + scheduler behavior
- Default max queue depth: `8`.
- `SCHED` appends `(lane, trigger_mm)` if room exists.
- Any queue entry implies scheduler state `ACTIVE`.
- `RESET_QUEUE` and effective mode changes clear queue and set scheduler `IDLE`.
- Busy host state emits canonical `NACK 7 BUSY`.

## Retry policy (spec JSON)
- ACK timeout: `100 ms`
- Max retries: `3`
- Backoff sequence: `[0, 50, 100] ms`
- On timeout: resend same frame, fail after retry budget.
