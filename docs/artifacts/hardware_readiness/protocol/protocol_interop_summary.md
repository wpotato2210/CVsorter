# Protocol interoperability summary

## Bench vs ESP32 hardware comparison

| Metric | Bench | ESP32 hardware | Deviation |
|---|---:|---:|---|
| Required OpenSpec v3 commands passed (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`) | 4/4 | 4/4 | None |
| Unsupported frame variants observed | 0 | 0 | None |
| Required-command NACKs | 0 | 0 | None |
| RTT p95 (ms) | 13.9 | 16.4 | ESP32 +2.5 ms (UART + MCU scheduling overhead) |
| RTT p99 / max (ms) | 16.2 / 18.5 | 19.2 / 21.7 | ESP32 +3.0 / +3.2 ms (within transport budget) |

## ESP32 protocol RTT distribution evidence

- Primary trace: `hardware_protocol_trace.log` (`sample_count=500`, all required commands ACKed).
- Histogram capture: `esp32_protocol_rtt_distribution.csv`.
- Distribution is unimodal and stable around 10-14 ms; no long-tail spikes beyond 22 ms bucket.

## Deviation callouts

- Functional behavior remains parity-complete against bench: required commands and ACK metadata are equivalent.
- ESP32 latency overhead is expected from physical UART framing and FreeRTOS task scheduling.
- No protocol deviations that impact readiness gate pass/fail were observed.

## Verdict

PASS — protocol interoperability criterion requalified with ESP32-backed evidence.
