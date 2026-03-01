# Queue behavior summary

## Bench vs hardware comparison

| Check | Bench | Hardware | Deviation |
|---|---|---|---|
| Commands accepted before boundary (`queue_limit=16`) | 16/16 | 16/16 | None |
| Queue-full signal at attempt 17 | `NACK-6 QUEUE_FULL` | `NACK-6 QUEUE_FULL` | None |
| Unexpected drops before full boundary | 0 | 0 | None |
| Recovery after dequeue | Accepted 4/4 | Accepted 4/4 | None |
| Recovery after `RESET_QUEUE` | `queue_depth=0` | `queue_depth=0` | None |

## Deviation callouts

- No behavioral divergence across bench and hardware queue handling.
- Hardware queue telemetry timestamps showed ~2-4 ms additional inter-command spacing versus bench; this did not affect acceptance ordering or recovery semantics.

## Verdict

PASS — queue behavior criterion is met in both environments.
