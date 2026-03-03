# ESP32 SAFE/watchdog/NACK fault matrix

| Injected fault | Expected behavior | Observed on ESP32 | Pass |
|---|---|---|---|
| transport timeout (420 ms) | watchdog expiry causes `AUTO->SAFE` | `AUTO->SAFE` with operator recovery MANUAL->AUTO | Yes |
| queue saturation | canonical `NACK-6 QUEUE_FULL` | `NACK-6 QUEUE_FULL` at queue_depth=16 | Yes |
| scheduler busy window | canonical `NACK-7 BUSY` only | `NACK-7 BUSY` with no alias details | Yes |
| uart disconnect (500 ms) | watchdog expiry causes `AUTO->SAFE` | `AUTO->SAFE` with operator recovery MANUAL->AUTO | Yes |
