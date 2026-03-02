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
- Queue state: `0..8` entries.
- Frame validation state: `valid | rejected` with deterministic reason.

## Dependencies
- `protocol.md` for command validation ranges and transition policy.
- `architecture.md` for CV pipeline ordering and scheduler handoff.
- Contract/schema assets under `contracts/` and `protocol/commands.json`.

## Key Behaviors / Invariants
- CV pipeline ordering is fixed: preprocess/calibration -> deploy -> eval -> scheduler -> serial wire.
- `SCHED` lane range is `0..21`; trigger range is `0.0..2000.0` mm.
- `SAFE -> AUTO` transition is forbidden.
- Mode changes and `RESET_QUEUE` clear queue and force scheduler to `IDLE`.
- All frame and command validation failures map to canonical NACK codes.

## Performance / Concurrency Risks
- High frame rate plus frequent triggers can saturate queue depth `8` and increase `QUEUE_FULL` events.
- Validation split across modules can drift and produce inconsistent NACK behavior if constraints are not treated as canonical.
- Parallel producers must not bypass queue-cap checks.

## Integration Points
- `src/coloursorter/deploy/pipeline.py` and `src/coloursorter/eval/rules.py` for frame-level acceptance.
- `src/coloursorter/scheduler/output.py` for trigger enqueue policy.
- `src/coloursorter/serial_interface/*` and protocol parser for frame integrity checks.

## Conflicts / Missing Links
- Servo timing budget and trigger jitter bounds are still unspecified.
- No explicit conformance gate currently guarantees spec/runtime parity for constraints.
