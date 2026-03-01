# OpenSpec v3 Telemetry Schema

Bench log records MUST include:
- `frame_timestamp`
- `trigger_timestamp`
- `trigger_mm`
- `lane_index`
- `rejection_reason`
- `belt_speed_mm_s`
- `queue_depth`
- `scheduler_state`
- `mode`

Additional compatibility fields may remain, but the fields above are mandatory for governance-complete telemetry.
