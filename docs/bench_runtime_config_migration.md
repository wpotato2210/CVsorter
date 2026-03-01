# Bench Runtime Config Migration (`default_config.yaml` -> `bench_runtime.yaml`)

Use `configs/bench_runtime.yaml` as the canonical startup file for bench runtime and GUI startup.

## Field migration map

| Legacy `configs/default_config.yaml` | New `configs/bench_runtime.yaml` |
|---|---|
| `motion_mode` | `motion_mode` |
| `homing_mode` | `homing_mode` |
| `bench_transport` | `transport.kind` |
| `serial_port` | `transport.serial.port` |
| `serial_baud` | `transport.serial.baud` |
| `serial_timeout_s` | `transport.serial.timeout_s` |
| *(not present)* | `frame_source.mode` |
| *(not present)* | `frame_source.replay_path` |
| *(not present)* | `frame_source.replay_frame_period_s` |
| *(not present)* | `camera.index` |
| *(not present)* | `camera.frame_period_s` |
| *(not present)* | `transport.max_queue_depth` |
| *(not present)* | `transport.base_round_trip_ms` |
| *(not present)* | `transport.per_item_penalty_ms` |
| *(not present)* | `cycle_timing.period_ms` |
| *(not present)* | `cycle_timing.queue_consumption_policy` |
| *(not present)* | `scenario_thresholds.*` |

## Notes

- `default_config.yaml` has product-level thresholds (`defect_thresholds`, `belt_speed_mm_s`, `camera_to_reject_mm`) that are not consumed by bench controller startup.
- Bench startup now requires nested sections for `frame_source`, `camera`, `transport`, `cycle_timing`, and `scenario_thresholds`.
- Enum validation is unchanged for `motion_mode` and `homing_mode`, and numeric/range checks are now explicit for startup fields.
