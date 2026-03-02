# constraints.md

## Purpose
Define authoritative correctness constraints for the ColourSorter CV pipeline, scheduler, and MCU protocol boundary so frame handling and trigger generation remain deterministic.

## Inputs / Outputs
- **Inputs**
  - Frame metadata and detection payloads from CV ingest.
  - Runtime configs (`configs/default_config.yaml`, `configs/bench_runtime.yaml`, `configs/lane_geometry.yaml`, `configs/calibration.json`).
  - Wire command requests (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`).
- **Outputs**
  - Validated `DecisionPayload` and scheduler commands in canonical `SCHED:<lane>:<position_mm>` form.
  - Canonical ACK/NACK outcomes for invalid arguments, malformed frame data, and queue/mode violations.

## States
- Mode state: `AUTO | MANUAL | SAFE`.
- Scheduler state: `IDLE | ACTIVE`.
- Queue state: `0..8` entries per `protocol.md` default host contract.
- Frame validation state: `valid | rejected` with deterministic reason.

## Dependencies
- `protocol.md` for command validation ranges and transition policy.
- `architecture.md` for CV pipeline ordering and scheduler handoff.
- `threading_model.md` for synchronization/serialization assumptions.
- Contract/schema assets under `contracts/` and `protocol/commands.json`.

## Key Behaviors / Invariants
- CV pipeline ordering is fixed: preprocess/calibration -> deploy -> eval -> scheduler -> serial wire.
- `SCHED` lane range is `0..21`; trigger range is `0.0..2000.0` mm.
- `SAFE -> AUTO` transition is forbidden.
- Mode changes and `RESET_QUEUE` clear queue and force scheduler to `IDLE`.
- All frame and command validation failures map to canonical NACK codes.

## Performance / Concurrency Risks
- High frame rate plus frequent triggers can saturate queue depth and increase `QUEUE_FULL` events.
- Validation split across modules can drift and produce inconsistent NACK behavior if constraints are not treated as canonical.
- Parallel producers must not bypass queue-cap checks.

## Cross-layer dependency notes
- `state_model.md` transition definitions are the source for mode/scheduler state legality.
- `error_model.md` must remain consistent with the same NACK mapping and recovery assumptions.
- `testing_strategy.md` should encode these constraints as executable assertions.

## Open questions (requires input)
- Max/min queue depth differs across artifacts (`8` in host defaults vs `16` in hardware readiness stress checks): which depth is authoritative per mode/environment?
- Required frame-to-trigger latency budget per mode (`AUTO`, `MANUAL`, `SAFE`) is not explicitly defined.
- Constraints on parallel frame processing / parallel command handling throughput are not specified.
- Servo timing constraints (actuation delay, minimum pulse interval, jitter limits) are not codified.

## Conflicts / Missing Links
- No explicit conformance gate currently guarantees spec/runtime parity for constraints.
