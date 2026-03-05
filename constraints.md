# constraints.md

## Canonical bounds
This document inherits all numeric and state constraints from `openspec.md` without deviation.

- `fps_target=100`
- `max_latency_ms<=15`
- `max_actuator_pulse_ms<=1`
- `queue_depth=8`
- `heartbeat_period_ms<=50`
- `heartbeat_timeout_ms<=150`

## State invariants
- Required states: `AUTO`, `MANUAL`, `SAFE`, `ESTOP_ACTIVE`, `SAFE_LATCH`, `IDLE`, `ACTIVE`
- `ESTOP_ACTIVE` always implies motion inhibition.
- `SAFE_LATCH` persists until authenticated reset by authorized operator.

## Timing invariants
- `frame_timestamp_ms`: capture timebase
- `pipeline_latency_ms`: bounded by `max_latency_ms`
- `trigger_offset_ms`: deterministic scheduling offset
- `actuation_delay_ms`: deterministic actuator delay contribution

## Auth invariants
Motion-capable commands require `auth_id`, `auth_ts_ms`, `auth_nonce`, `auth_tag` and replay rejection.
