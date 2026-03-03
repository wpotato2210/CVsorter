# Timing budget summary

## Bench vs ESP32 hardware comparison

| Stage | Bench P95 / Max (ms) | ESP32 P95 / Max (ms) | Budget (ms) | Deviation |
|---|---:|---:|---:|---|
| ingest | 4.3 / 6.2 | 5.3 / 7.4 | 8.0 | ESP32 +1.0 / +1.2 |
| decision | 6.8 / 9.7 | 7.9 / 11.1 | 12.0 | ESP32 +1.1 / +1.4 |
| schedule | 3.5 / 5.1 | 4.4 / 6.1 | 8.0 | ESP32 +0.9 / +1.0 |
| transport | 8.9 / 12.4 | 13.6 / 19.2 | 20.0 | ESP32 +4.7 / +6.8 |
| cycle | 22.1 / 30.5 | 30.8 / 41.9 | 45.0 | ESP32 +8.7 / +11.4 |

## ESP32 scheduler timing envelope evidence

- Stage budget file: `hardware_timing_budget.csv`.
- Envelope capture: `esp32_scheduler_timing_envelope.csv` confirms scheduler dispatch, jitter, and full cycle envelope remain within OpenSpec v3 limits.
- Highest observed stress point remains transport stage max=19.2 ms, still below 20.0 ms budget.

## Deviation callouts

- ESP32 is consistently slower than bench, with largest delta in transport due to UART and firmware scheduling jitter.
- All ESP32 P95 and max values remain within stage and cycle budgets.
- No timing-budget deviation requires mitigation for readiness gate.

## Verdict

PASS — timing criterion satisfied and requalified on ESP32 hardware evidence.
