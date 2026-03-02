# constraints.md

## Purpose
Define authoritative correctness constraints for the ColourSorter CV pipeline, scheduler, and MCU protocol boundary so frame handling and trigger generation remain deterministic.

## Inputs / Outputs
- **Inputs**
  - Frame metadata and detection payloads from CV ingest.
  - Runtime configs (`configs/default_config.yaml`, `configs/bench_runtime.yaml`, `configs/lane_geometry.yaml`, `configs/calibration.json`).
  - Wire command requests (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`).
- **Outputs**
  - Validated `DecisionPayload` and scheduler commands in canonical scheduler projection `SCHED:<lane>:<position_mm>`.
  - Protocol-compliant wire frames at transport boundary (`<SCHED|lane|trigger_mm>`).
  - Canonical ACK/NACK outcomes for invalid arguments, malformed frame data, and queue/mode violations.

## States
- Mode state: `AUTO | MANUAL | SAFE`.
- Scheduler state: `IDLE | ACTIVE`.
- Queue state: `0..8` entries.
- Frame validation state: `valid | rejected` with deterministic reason.

## Dependencies
- `protocol.md` for command validation ranges and transition policy.
- `architecture.md` for CV pipeline ordering and scheduler handoff.
- `threading_model.md` for synchronization assumptions around queue/state mutation.
- Contract/schema assets under `contracts/` and `protocol/commands.json`.

## Key Behaviors / Invariants
- CV pipeline ordering is fixed: preprocess/calibration -> deploy -> eval -> scheduler -> serial wire.
- `SCHED` lane range is `0..21`; trigger range is `0.0..2000.0` mm.
- `SAFE -> AUTO` transition is forbidden.
- Mode changes and `RESET_QUEUE` clear queue and force scheduler to `IDLE`.
- All frame and command validation failures map to canonical NACK codes.

## Cross-layer Dependency Notes
- `state_model.md` depends on these bounds to keep `queue_depth` and `scheduler_state` coherent.
- `error_model.md` consumes constraint violations to emit deterministic NACK code/detail pairs.
- `deployment.md` must preserve these invariants across bench/staging/production without environment-specific semantic drift.

## Performance / Concurrency Notes
- High frame rate plus frequent triggers can saturate queue depth `8` and increase `QUEUE_FULL` events.
- Validation split across modules can drift and produce inconsistent NACK behavior if constraints are not treated as canonical.
- Parallel producers must not bypass queue-cap checks.

## Open Questions (requires input)
- Max/min queue depth and frame-to-trigger latency budget per mode (`AUTO`, `MANUAL`, `SAFE`).
- Constraints on frame processing throughput and allowable parallel task count.
- Servo timing/physical actuation limits (minimum trigger spacing, tolerated jitter, max duty cycle).

## Conflicts / Missing Links
- No explicit conformance gate currently guarantees protocol/spec/runtime parity for constraints.
