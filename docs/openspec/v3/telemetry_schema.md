# OpenSpec v3 Telemetry Schema

Bench log records MUST include:
- `frame_timestamp`
- `trigger_generation_timestamp`
- `trigger_timestamp`
- `trigger_mm`
- `lane_index`
- `rejection_reason`
- `belt_speed_mm_s`
- `queue_depth`
- `scheduler_state`
- `mode`

Trigger timing model expectations:
- `trigger_generation_timestamp` is anchored to the latest observed encoder pulse timestamp (or the previous frame timestamp if no pulse has been observed yet).
- `trigger_timestamp` is projected from `trigger_generation_timestamp + schedule_time + travel_time`.
- `travel_time` is derived from encoder scale (`pulses_per_revolution`, `pulley_circumference_mm`) and configured belt speed.
- Under zero-speed faults, projection is deterministic and remains equal to `trigger_generation_timestamp`.

Reference runtime emitters:
- Runtime log model: `src/coloursorter/bench/types.py::BenchLogEntry`
- Cycle production path: `src/coloursorter/bench/runner.py::BenchRunner.run_cycle`
- Encoder timing model: `src/coloursorter/bench/virtual_encoder.py::VirtualEncoder`
- Artifact export: `src/coloursorter/bench/evaluation.py::write_artifacts`

Validation tests:
- `tests/test_determinism_and_telemetry.py::test_bench_logs_include_required_telemetry_fields`
- `tests/test_determinism_and_telemetry.py::test_projected_trigger_timestamp_is_deterministic_at_low_speed`
- `tests/test_determinism_and_telemetry.py::test_projected_trigger_timestamp_stops_advancing_under_zero_speed_fault`
- `tests/test_determinism_and_telemetry.py::test_trigger_generation_timestamp_uses_previous_pulse_when_dropout_hides_current_interval`
- `tests/test_bench_evaluation.py::test_telemetry_csv_includes_required_openspec_v3_fields`

Additional compatibility fields may remain, but the fields above are mandatory for governance-complete telemetry.


Extended hardening telemetry fields (non-breaking additions):
- `ingest_latency_ms`
- `decision_latency_ms`
- `schedule_latency_ms`
- `transport_latency_ms`
- `cycle_latency_ms`
- `nack_code`
- `nack_detail`
