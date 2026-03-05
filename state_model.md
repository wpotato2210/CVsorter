# state_model.md

## Runtime states
- Mode: `AUTO | MANUAL | SAFE`
- Safety: `ESTOP_ACTIVE`, `SAFE_LATCH`
- Scheduler: `IDLE | ACTIVE`

## Transitions
- E-STOP event: `* -> ESTOP_ACTIVE + SAFE_LATCH`
- While `SAFE_LATCH` active: motion transitions and motion commands are denied.
- Authenticated reset authority may clear `SAFE_LATCH` and return to `SAFE`.
- From `SAFE`, authenticated operator can transition to `MANUAL` or `AUTO`.

## Queue and timing state fields
- `queue_depth` range is exactly `0..8`
- Timing fields carried with scheduling decisions:
  - `frame_timestamp_ms`
  - `pipeline_latency_ms`
  - `trigger_offset_ms`
  - `actuation_delay_ms`
