# OpenSpec v3 Timing Budget

## Bench transport targets
- ACK timeout budget: 100 ms.
- Retry count: 3 max attempts.
- Backoff sequence: 0 ms, 50 ms, 100 ms.

## Runtime latency targets
- Typical protocol RTT budget: <= 10 ms in mock bench mode.
- Peak RTT budget: <= 20 ms in nominal bench scenarios.
- Queue jitter budget: deterministic per-item penalty model with explicit queue depth telemetry.

## Determinism constraints
- Encoder pulse generation uses accumulator arithmetic (no per-cycle truncation drift).
- Zero-speed and missing-pulse paths must emit stable trigger timestamps.

## Validation references
- Retry + timeout behavior: `tests/test_serial_transport.py`
- Nominal RTT envelope and trigger timestamp flow: `tests/test_integration.py`
- Deterministic encoder behavior: `tests/test_determinism_and_telemetry.py`


## Stage observability
- Ingest, decision, schedule, transport, and cycle timings are emitted per bench log entry.
- Validation reference: `tests/test_determinism_and_telemetry.py::test_stage_latency_fields_are_populated_for_each_log`.
