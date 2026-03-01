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
