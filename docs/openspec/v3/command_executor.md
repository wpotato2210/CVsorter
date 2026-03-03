# OpenSpec v3 Firmware Command Executor Export

## Command handling sequence
1. Parse framed packet and validate CRC/message id.
2. Deduplicate by `msg_id` and return cached ACK/NACK for repeats.
3. Dispatch command in deterministic order: `HELLO`, `HEARTBEAT`, `SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`.
4. Emit ACK/NACK using canonical OpenSpec v3 code mappings.

## Command matrix
| Command | Preconditions | Action | Response |
|---|---|---|---|
| `HELLO` | protocol version `3.1` | negotiate capabilities | `ACK` / NACK(3/4) |
| `HEARTBEAT` | protocol synced | refresh link timer | `ACK` / NACK(5) |
| `SET_MODE` | legal transition | update mode, optional queue clear | `ACK` / NACK(5) |
| `SCHED` | link ready + queue capacity | enqueue lane/trigger job | `ACK` / NACK(6/7) |
| `GET_STATE` | none | return mode/queue/link snapshot | `ACK` |
| `RESET_QUEUE` | none | clear scheduler queue | `ACK` |

## Timing annotations
- Parse + dedupe lookup: **<= 30 us**.
- `SCHED` enqueue path: **<= 40 us**.
- ACK serialization + UART enqueue: **<= 25 us**.
