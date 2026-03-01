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

Reference runtime emitters:
- Runtime log model: `src/coloursorter/bench/types.py::BenchLogEntry`
- Cycle production path: `src/coloursorter/bench/runner.py::BenchRunner.run_cycle`
- Artifact export: `src/coloursorter/bench/evaluation.py::write_artifacts`

Validation tests:
- `tests/test_determinism_and_telemetry.py::test_bench_logs_include_required_telemetry_fields`
- `tests/test_bench_evaluation.py::test_telemetry_csv_includes_required_openspec_v3_fields`

Additional compatibility fields may remain, but the fields above are mandatory for governance-complete telemetry.
