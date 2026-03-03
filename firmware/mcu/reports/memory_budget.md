# Firmware Memory Budget Report

| Budget Item | Limit | Measured / Allocated | Margin |
|---|---:|---:|---:|
| Stack (worst-case ISR + scheduler) | 4096 B | 2688 B | 1408 B |
| Heap (runtime) | 2048 B | 512 B | 1536 B |
| Queue occupancy (worst-case commands) | 8 slots | 8 slots | 0 slots |
| UART RX ring buffer | 256 B | 224 B high-water mark | 32 B |

## Notes
- Worst-case queue occupancy assumes burst of `SCHED` commands before actuator drain.
- Stack estimate includes watchdog, brownout sampling, UART ISR, and command executor path.
