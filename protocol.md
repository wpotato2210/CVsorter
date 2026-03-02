# protocol.md

## Scope
Reverse-engineered host↔MCU protocol reference for ChatGPT workstreams.

## Frozen I/O
### Input (host → MCU)
- Wire frame: `<CMD|arg1|arg2>` (ASCII, `|` delimiter, `<`/`>` envelope).
- Commands: `SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`.

### Output (MCU → host)
- ACK: `<ACK|mode|queue_depth|scheduler_state|queue_cleared>`
- NACK: `<NACK|code|detail>`

## Dependencies
- Contract artifact: `protocol/commands.json`
- Host protocol model: `src/coloursorter/protocol/host.py`
- Constants/policy: `src/coloursorter/protocol/constants.py`, `src/coloursorter/protocol/policy.py`, `src/coloursorter/protocol/nack_codes.py`
- Frame parser/serializer: `src/coloursorter/serial_interface/serial_interface.py`
- Schedule encoder: `src/coloursorter/serial_interface/wire.py`

## Command contract
| Command | Args | Validation | Side effects |
| --- | --- | --- | --- |
| `SET_MODE` | `mode` | arg count = 1, enum in `AUTO|MANUAL|SAFE`, transition policy check | On effective mode change: clear queue, set scheduler `IDLE` |
| `SCHED` | `lane`, `trigger_mm` | arg count = 2, `lane ∈ [0,21]`, `trigger_mm ∈ [0.0,2000.0]`, queue capacity check | append queue item, set scheduler `ACTIVE` |
| `GET_STATE` | none | arg count = 0 | return current mode/queue/scheduler snapshot |
| `RESET_QUEUE` | none | arg count = 0 | clear queue, set scheduler `IDLE` |

## Named variables (canonical)
- `mode`: `AUTO|MANUAL|SAFE`
- `queue_depth`: decimal string of queue length
- `scheduler_state`: `IDLE|ACTIVE`
- `queue_cleared`: `true|false`
- `lane`: integer lane index
- `trigger_mm`: millimeter target (3 dp precision at serialization boundary)

## NACK code map
| Code | Detail |
| --- | --- |
| `1` | `UNKNOWN_COMMAND` |
| `2` | `ARG_COUNT_MISMATCH` |
| `3` | `ARG_RANGE_ERROR` |
| `4` | `ARG_TYPE_ERROR` |
| `5` | `INVALID_MODE_TRANSITION` |
| `6` | `QUEUE_FULL` |
| `7` | `BUSY` |
| `8` | `MALFORMED_FRAME` |

## Mode transition policy
| From \ To | AUTO | MANUAL | SAFE |
| --- | --- | --- | --- |
| `AUTO` | ✅ | ✅ | ✅ |
| `MANUAL` | ✅ | ✅ | ✅ |
| `SAFE` | ❌ (`NACK 5`) | ✅ | ✅ |

## Queue and retry policy
- `max_queue_depth` default: `8`
- Host busy gate: return canonical `NACK|7|BUSY`
- Retry policy in contract JSON: `ack_timeout_ms=100`, `max_retries=3`, `backoff_ms=[0,50,100]`
