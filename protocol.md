# protocol.md

## Wire Format
- ASCII only.
- Tokens are uppercase.
- Token separator is a single ASCII space (`0x20`).
- Line ending is exactly `\n`.
- No trailing spaces.

### Versioned responses
| Version | Allowed responses | Payload policy |
| --- | --- | --- |
| v1 | `OK`, `ERR` | No payloads permitted. |
| v2 | `ACK_OK`, `ACK_BUSY`, `ERR_RANGE`, `ERR_TYPE`, `ERR_MODE`, `ERR_QUEUE`, `ERR_FRAME`, `ERR_UNKNOWN` | `ACK_*` must not include payloads. `ERR_*` may include one payload token only when the response definition requires detail text. |

`CAPS?` deterministic form (v2):
- Fixed key order: `VER`, `RESP`, `PAYLOAD`.
- Exact string form: `CAPS VER=v2 RESP=<comma-separated response tokens> PAYLOAD=ERR_*:DETAIL`.
- No extra keys, no key reordering, no lowercase.

Canonical parser-fixture examples:
```text
OK\n
ACK_BUSY\n
CAPS VER=v2 RESP=ACK_OK,ACK_BUSY,ERR_RANGE,ERR_TYPE,ERR_MODE,ERR_QUEUE,ERR_FRAME,ERR_UNKNOWN PAYLOAD=ERR_*:DETAIL\n
```

## Link timing and watchdog
- `heartbeat_period_ms<=50`
- `heartbeat_timeout_ms<=150`
- Timeout escalation sets `ESTOP_ACTIVE` and `SAFE_LATCH`.

## Motion-capable command security
Commands that can produce motion must include:
- `auth_id`
- `auth_ts_ms`
- `auth_nonce`
- `auth_tag`

Replay-protection is mandatory: reject duplicate or stale `(auth_id, auth_nonce, auth_ts_ms)` tuples.

## State-report contract
`GET_STATE`/ACK payload exposes:
- `mode`
- `queue_depth` (`0..8`)
- `scheduler_state`
- `estop_state` (`ESTOP_ACTIVE` clear/set)
- `safe_latch_state` (`SAFE_LATCH` clear/set)

## Timing-report contract
Motion path telemetry includes:
- `frame_timestamp_ms`
- `pipeline_latency_ms` (must satisfy `<=15`)
- `trigger_offset_ms`
- `actuation_delay_ms`
