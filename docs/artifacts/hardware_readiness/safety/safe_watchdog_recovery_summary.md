# SAFE/watchdog recovery summary

## Bench vs ESP32 hardware comparison

| Scenario | Bench result | ESP32 hardware result | Deviation |
|---|---|---|---|
| Transport timeout fault | AUTO->SAFE, recovered MANUAL->AUTO | AUTO->SAFE, recovered MANUAL->AUTO | None |
| Queue saturation fault | `NACK-6 QUEUE_FULL` | `NACK-6 QUEUE_FULL` | None |
| Busy-lock fault | Canonical `NACK-7 BUSY` | Canonical `NACK-7 BUSY` | None |
| Watchdog-triggered safe fallback | Triggered and latched SAFE | Triggered and latched SAFE | None |
| Operator recovery without process restart | Yes | Yes | None |

## ESP32 SAFE/WATCHDOG/NACK fault behavior evidence

- Fault log: `hardware_fault_injection.log` covers timeout, queue saturation, busy lock, and UART disconnect cases.
- Matrix capture: `esp32_safe_watchdog_nack_fault_matrix.md` provides expected-vs-observed outcomes.
- Canonicalization requirement is preserved: `NACK-7` appears only as `BUSY` detail.

## Deviation callouts

- Injection methods remain environment-specific (bench can inject protocol-level anomalies directly, ESP32 uses physical transport perturbation), but required state and protocol outcomes align.
- No recovery-path divergence was observed.

## Verdict

PASS — SAFE/watchdog criterion requalified with ESP32-backed fault behavior evidence.
