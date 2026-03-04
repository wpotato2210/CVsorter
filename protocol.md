# protocol.md

## Frame format
- Wire frame: `<msg_id|CMD|payload|CRC32>`.
- `payload` is comma-separated positional arguments.
- `CRC32` is computed over `msg_id|CMD|payload` (ASCII, uppercase hex).

## Startup handshake
1. Host sends `HELLO(version, capabilities)`.
2. MCU validates protocol version and capability overlap.
3. Host sends periodic `HEARTBEAT`.
4. `SCHED` is rejected until handshake succeeds.

## Duplicate suppression
- MCU caches recent responses by `msg_id`.
- Replayed frame with same `msg_id` returns cached ACK/NACK and is **not re-executed**.

## Link-state FSM
- States: `DISCONNECTED`, `SYNCING`, `READY`, `DEGRADED`.
- `HELLO` transitions to `SYNCING`.
- Timely `HEARTBEAT` transitions/maintains `READY`.
- Heartbeat timeout transitions to `DEGRADED`.
- No sync transitions to `DISCONNECTED`.

## Commands
- `HELLO(version, capabilities)`
- `HEARTBEAT()`
- `SET_MODE(mode)`
- `SCHED(lane, trigger_mm)`
- `GET_STATE()`
- `RESET_QUEUE()`

ACK includes: `mode, queue_depth, scheduler_state, queue_cleared, link_state`.

## Artifact authority
- Authoritative protocol contract: `docs/openspec/v3/protocol/commands.json`.
- `protocol/commands.json` is a generated mirror for compatibility tooling and must stay byte-identical to the authoritative artifact.
- Implementations must use canonical tokens (`<msg_id|CMD|payload|CRC32>`, `ACK`, `NACK`) exactly as defined by the authoritative artifact.
