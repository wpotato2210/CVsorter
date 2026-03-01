# Protocol interoperability summary

## Bench vs hardware comparison

| Metric | Bench | Hardware | Deviation |
|---|---:|---:|---|
| Required OpenSpec v3 commands passed (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`) | 4/4 | 4/4 | None |
| Unsupported frame variants observed | 0 | 0 | None |
| Required-command NACKs | 0 | 0 | None |
| Average RTT (ms) | 8 | 11 | Hardware +3 ms (expected UART overhead) |
| Peak RTT (ms) | 17 | 23 | Hardware +6 ms (within transport budget) |

## Deviation callouts

- Functional behavior is parity-complete: both bench and hardware accepted all required commands with matching ACK metadata.
- Hardware RTT is slightly higher than bench due to physical serial transport and MCU processing jitter; this is expected and does not change protocol correctness.
- No protocol deviations that impact readiness gate pass/fail were observed.

## Verdict

PASS — protocol interoperability criterion satisfied on both environments.
