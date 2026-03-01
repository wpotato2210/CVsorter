# ColourSorter OpenSpec v3 Interface Control Document (ICD)

## Scope
This ICD defines host-to-MCU wire interfaces and runtime telemetry interfaces used by ColourSorter OpenSpec v3 bench and serial transport paths.

## Host ↔ MCU wire interface
- Framing: `<CMD|arg1|arg2>` ASCII packets.
- Commands: `SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`.
- ACK payload: `ACK|mode|queue_depth|scheduler_state|queue_cleared`.
- NACK payload: `NACK|nack_code|detail`.
- Canonical NACK code `7` means `BUSY` only (`NACK|7|BUSY`).
- Non-canonical `NACK|7|WATCHDOG` is interpreted as SAFE by bench transport to prevent misclassifying malformed busy replies.
- WATCHDOG is represented as a transport timeout fault state, not as a NACK code alias.

### Source of truth
- Protocol artifact: `docs/openspec/v3/protocol/commands.json`.
- Runtime host model: `src/coloursorter/protocol/host.py`.
- Runtime parser/serializer: `src/coloursorter/serial_interface/serial_interface.py`.
- Runtime schedule encoder: `src/coloursorter/serial_interface/wire.py`.

## Scheduler command interface
- Lane bounds: `0..21`.
- Trigger bounds: `0.0..2000.0` millimeters.

### Source of truth
- Runtime scheduler validation: `src/coloursorter/scheduler/output.py`.
- Host-side validation: `src/coloursorter/protocol/host.py`.

## Telemetry interface
Bench runtime telemetry CSV rows include required OpenSpec fields plus stage-level timing and raw NACK fidelity fields.

Required OpenSpec v3 fields:
- `frame_timestamp`
- `trigger_timestamp`
- `trigger_mm`
- `lane_index`
- `rejection_reason`
- `belt_speed_mm_s`
- `queue_depth`
- `scheduler_state`
- `mode`

Extended hardening fields:
- `ingest_latency_ms`
- `decision_latency_ms`
- `schedule_latency_ms`
- `transport_latency_ms`
- `cycle_latency_ms`
- `nack_code`
- `nack_detail`

### Source of truth
- Bench telemetry model: `src/coloursorter/bench/types.py`.
- Bench cycle emission: `src/coloursorter/bench/runner.py`.
- CSV artifact writer: `src/coloursorter/bench/evaluation.py`.
