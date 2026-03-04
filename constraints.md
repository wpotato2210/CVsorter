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

## Terminology Alignment (protocol + architecture)
- Canonical command and state names match `protocol.md` exactly: `SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`, `AUTO`, `MANUAL`, `SAFE`, `IDLE`, `ACTIVE`.
- Pipeline ordering terminology matches `architecture.md`: preprocess/calibration -> deploy -> eval -> scheduler -> serial wire.
- Queue terms are explicit: **queue capacity** (configured limit), **queue depth** (current occupancy), **host busy** (temporary admission refusal).

## States
- Mode state: `AUTO | MANUAL | SAFE`.
- Scheduler state: `IDLE | ACTIVE`.
- Queue state: `0..8` entries (default protocol value; authoritative depth owner is host/MCU ACK/GET_STATE).
- Frame validation state: `valid | rejected` with deterministic reason.

## Dependencies
- Queue-depth authority is defined in `docs/openspec/v3/state_machine.md` (Queue-depth authority section).
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
- `testing_strategy.md` must assert these values in unit + integration gates.
- `data_model.md` must persist queue/state fields with identical names and ranges.
- `deployment.md` must preserve these invariants across bench/staging/production without environment-specific semantic drift.

## Performance / Concurrency Notes
- High frame rate plus frequent triggers can saturate queue depth and increase `QUEUE_FULL` events.
- Validation split across modules can drift and produce inconsistent NACK behavior if constraints are not canonicalized.
- Parallel producers must not bypass queue-cap checks.

## Open Questions (requires input)
- **Execution model:** single-threaded event loop vs multi-threaded producer/consumer with explicit lock/atomic boundaries.
- **Authoritative queue sizing:** who owns effective queue capacity (`protocol/commands.json`, runtime config, or MCU firmware), and can it vary by stage/mode.
- **Timing/servo constraints:** minimum trigger spacing, max tolerated jitter, and actuator duty-cycle guardrails.
- **Latency budgets:** frame-to-trigger SLA by mode (`AUTO`, `MANUAL`, `SAFE`) and rejection/escalation behavior on breaches.

## Conflicts / Missing Links
- No explicit conformance gate currently guarantees protocol/spec/runtime parity for constraints.
