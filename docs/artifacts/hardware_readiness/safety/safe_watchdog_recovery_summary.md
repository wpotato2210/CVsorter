# SAFE/watchdog recovery summary

## Bench vs hardware comparison

| Scenario | Bench result | Hardware result | Deviation |
|---|---|---|---|
| Transport timeout fault | AUTO->SAFE, recovered MANUAL->AUTO | AUTO->SAFE, recovered MANUAL->AUTO | None |
| Watchdog-triggered safe fallback | Triggered and latched SAFE | Triggered and latched SAFE | None |
| Operator recovery without process restart | Yes | Yes | None |
| Secondary injected fault | Noncanonical NACK-7 watchdog detail normalized to timeout fault | UART disconnect (400 ms) watchdog timeout | Injection method differs; expected per environment |

## Deviation callouts

- Bench used protocol-level noncanonical NACK watchdog detail to validate normalization path, while hardware used physical UART disconnect to produce the watchdog timeout.
- Although injection method differed, observable recovery behavior matched: both converged to SAFE and recovered via MANUAL then AUTO with no process restart.

## Verdict

PASS — SAFE/watchdog criterion satisfied with cross-environment behavioral parity.
