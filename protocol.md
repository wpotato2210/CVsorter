# protocol.md

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
