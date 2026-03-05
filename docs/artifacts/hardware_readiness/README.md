# Hardware Readiness Artifacts

This directory stores checked-in evidence for `docs/hardware_readiness_gate.md` and deployment go/no-go decisions.

Expected structure:

- `protocol/` protocol traces and interoperability summary
- `queue/` queue stress logs and summary
- `safety/` SAFE/watchdog fault-injection logs and summary
- `timing/` timing budget exports and summary
- deployment acceptance bundle (latency/throughput/E-STOP thresholds + config snapshot)

## Required Traceability Fields
Every acceptance artifact bundle must include:
- `frame_timestamp_ms`
- `pipeline_latency_ms`
- `trigger_offset_ms`
- `actuation_delay_ms`
- threshold verdicts for latency/throughput/E-STOP
- reference to config snapshot conforming to `contracts/pipeline_runtime_config_schema.json`

Run `python tools/hardware_readiness_report.py` to summarize completeness.
