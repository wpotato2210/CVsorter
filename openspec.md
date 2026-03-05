# openspec.md

## Normative authority
`openspec.md` is the normative source of truth for runtime safety, timing, and protocol contracts. All secondary design docs (`constraints.md`, `architecture.md`, `state_model.md`, `protocol.md`, `security_model.md`) must mirror these values exactly.

## Required constants
- `fps_target=100`
- `max_latency_ms<=15`
- `max_actuator_pulse_ms<=1`
- `queue_depth=8`
- `heartbeat_period_ms<=50`
- `heartbeat_timeout_ms<=150`

## Required states and timing variables
- States: `AUTO`, `MANUAL`, `SAFE`, `ESTOP_ACTIVE`, `SAFE_LATCH`, `IDLE`, `ACTIVE`
- Timing variables: `frame_timestamp_ms`, `pipeline_latency_ms`, `trigger_offset_ms`, `actuation_delay_ms`

## Safety semantics
- Any E-STOP assertion transitions to `ESTOP_ACTIVE` and engages `SAFE_LATCH`.
- Motion commands are blocked while `ESTOP_ACTIVE` or `SAFE_LATCH` is set.
- Leaving `SAFE_LATCH` requires explicit reset authority and authenticated reset command.

## Command authentication
All motion-capable commands (`SCHED`, mode transitions that enable motion, queue-reset affecting motion resumption) must carry:
- `auth_id`
- `auth_ts_ms`
- `auth_nonce`
- `auth_tag`

Anti-replay validation is mandatory using `(auth_id, auth_nonce, auth_ts_ms)` uniqueness + timeout windows.
