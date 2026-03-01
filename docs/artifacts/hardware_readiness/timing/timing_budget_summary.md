# Timing budget summary

## Bench vs hardware comparison

| Stage | Bench P95 / Max (ms) | Hardware P95 / Max (ms) | Budget (ms) | Deviation |
|---|---:|---:|---:|---|
| ingest | 4.3 / 6.2 | 5.0 / 7.1 | 8.0 | Hardware +0.7 / +0.9 |
| decision | 6.8 / 9.7 | 7.6 / 10.8 | 12.0 | Hardware +0.8 / +1.1 |
| schedule | 3.5 / 5.1 | 4.1 / 6.3 | 8.0 | Hardware +0.6 / +1.2 |
| transport | 8.9 / 12.4 | 12.8 / 18.6 | 20.0 | Hardware +3.9 / +6.2 |
| cycle | 22.1 / 30.5 | 29.4 / 39.7 | 45.0 | Hardware +7.3 / +9.2 |

## Deviation callouts

- Hardware is consistently slower than bench, with the largest delta in transport stage due to UART and firmware scheduling jitter.
- All hardware P95 and max values remain within OpenSpec v3 stage and cycle budgets.
- No timing-budget deviation requires mitigation for release readiness.

## Verdict

PASS — timing criterion satisfied for both bench and hardware runs.
