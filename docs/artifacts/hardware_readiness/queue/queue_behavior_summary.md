# Queue behavior summary

## Bench vs ESP32 hardware comparison

| Check | Bench | ESP32 hardware | Deviation |
|---|---|---|---|
| Commands accepted before boundary (`queue_limit=16`) | 16/16 | 16/16 | None |
| Queue-full signal at attempt 17 | `NACK-6 QUEUE_FULL` | `NACK-6 QUEUE_FULL` | None |
| Unexpected drops before full boundary | 0 | 0 | None |
| ACK/NACK stability under load (10 s, 40 Hz burst) | Stable (`NACK-6` only at saturation) | Stable (`ack_ratio=94.23%`, `nack_other=0`) | None |
| Recovery after dequeue | Accepted 4/4 | Accepted 4/4 | None |
| Recovery after `RESET_QUEUE` | `queue_depth=0` | `queue_depth=0` | None |

## ESP32 ACK/NACK load evidence

- Run log: `hardware_queue_stress.log` captures saturation and recovery phases.
- Windowed capture: `esp32_ack_nack_stability_under_load.csv` shows only canonical queue-full NACKs while loaded.
- No non-canonical or unexpected NACK codes were observed during the stress profile.

## Deviation callouts

- No behavioral divergence across bench and ESP32 queue handling.
- ESP32 inter-command spacing is slightly higher than bench under burst load but does not affect ordering, boundary handling, or recovery semantics.

## Verdict

PASS — queue behavior criterion is met and requalified on ESP32 evidence.
