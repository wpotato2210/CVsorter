# Protocol divergence report (OpenSpec host ↔ MCU)

## Section A: Missing or extra commands

### A1. Canonical command set (spec)
- OpenSpec v3 defines six protocol commands: `HELLO`, `HEARTBEAT`, `SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`.
- Startup handshake required by spec artifact is `HELLO`, then `HEARTBEAT`.

### A2. Host implementation command set
- `OpenSpecV3Host` dispatch table implements exactly the same six commands.

### A3. Transport implementation command set
- `SerialMcuTransport` uses those six commands (`HELLO`, `HEARTBEAT`, `GET_STATE`, `RESET_QUEUE`, `SET_MODE`, `SCHED`) in handshake/sync/send paths.
- `send_command(command: str, ...)` accepts arbitrary command strings, so the API surface is broader than the canonical spec despite internal paths using canonical constants.

### A4. Tests command expectations
- Tests validate the six canonical commands.
- Tests also intentionally send `UNKNOWN` command to validate NACK semantics; this is a negative test command, not part of OpenSpec canonical command list.

### A5. Command-set divergence summary
- Spec-only commands missing in host/transport: **none**.
- Implemented but not in spec (positive path): **none**.
- Commands used in tests but not in spec: **`UNKNOWN`** (intentional negative-path coverage).

## Section B: Handshake sequence violations

Expected sequence under this audit:
`HELLO -> HEARTBEAT -> GET_STATE -> RESET_QUEUE -> SET_MODE -> SCHED`

### B1. Conditional skip of RESET_QUEUE/SET_MODE
- Current transport executes `GET_STATE`, then conditionally runs `RESET_QUEUE` and/or `SET_MODE` only when mode/queue conditions require it.
- If mode already matches and queue is empty, sequence becomes `HELLO -> HEARTBEAT -> GET_STATE -> SCHED`, skipping `RESET_QUEUE` and `SET_MODE`.

Risk: **Medium** (state sync still present, but not strict to expected deterministic sequence).

Minimal fix: enforce strict startup path with explicit no-op-safe `RESET_QUEUE` + `SET_MODE(expected_mode)` before first `SCHED`, even when already synchronized.

### B2. Extra HEARTBEATs in handshake path
- Link readiness sends `HEARTBEAT` on interval before sync checks; with `heartbeat_interval_s=0.0`, this is every send.
- Recovery path can also issue additional `HEARTBEAT` and repeated `HELLO`/`GET_STATE` sequences.

Risk: **Low/Medium** (protocol-safe but can make trace-level determinism harder and widen handshake variance).

Minimal fix: split one-time bootstrap handshake from periodic liveness heartbeats, and gate periodic heartbeat until post-bootstrap sync completion.

## Section C: Response contract mismatches

### C1. Host ACK/NACK contracts mostly align with strict OpenSpec schema
- ACK includes mode/queue_depth/scheduler_state/queue_cleared/link_state.
- NACK includes code/detail.

Risk: **Low**.

Minimal fix: none required for host path.

### C2. Serial parser allows bare `ACK` without metadata
- `parse_ack_tokens` accepts one-token `ACK`, while strict response schema requires ACK metadata (`mode`, `queue_depth`, `scheduler_state`, `queue_cleared`).

Risk: **Medium** (non-compliant firmware ACKs may be silently accepted).

Minimal fix: require metadata-bearing ACK in parser for protocol-v3 transport contexts.

### C3. Firmware transport contract diverges from OpenSpec metadata model
- MCU C dispatch response struct has `status`, `heartbeat_id`, and raw state snapshot; no OpenSpec wire-level `nack_code` range 1..8, no `queue_cleared` field, and scheduler state naming differs (`RUNNING` vs `ACTIVE`).
- Firmware mode enum exposes `SAFE/RUN/SERVICE` while OpenSpec mode contract is `AUTO/MANUAL/SAFE`.

Risk: **High** (direct host↔firmware interop depends on adapters/translation assumptions).

Minimal fix: add explicit adapter mapping layer (or firmware protocol shim) enforcing OpenSpec canonical enums and ACK/NACK payload semantics.

## Section D: Behavioural drift risks

### D1. Implicit default mode can mutate remote state
- Transport defaults expected mode to `AUTO`; during sync, mode mismatch triggers `SET_MODE(AUTO)` (and potentially `RESET_QUEUE`).

Risk: **Medium** (host startup can change device mode unexpectedly if MCU boots SAFE/MANUAL by policy).

Minimal fix: require explicit desired mode from runtime config/operator intent before first sync-mutating command.

### D2. Retry semantics depend on dedupe support
- Transport retries reuse same msg_id/payload after timeout.
- Host emulator implements dedupe by msg_id, but transport behavior against non-dedupe firmware could duplicate side effects (e.g., multiple `SCHED` enqueues).

Risk: **High** for non-dedupe targets.

Minimal fix: hard-require dedupe capability confirmation in HELLO negotiation and fail closed if missing.

### D3. Auto-recovery fallbacks can mask protocol integrity failures
- On heartbeat/sync failure transport re-handshakes and retries state sync automatically.

Risk: **Medium** (operationally resilient but can obscure recurrent contract faults and blur deterministic fault handling boundaries).

Minimal fix: cap auto-recovery attempts and emit structured fault state requiring operator acknowledgement after threshold.
