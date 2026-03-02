# styleguide.md

## Purpose
Define deterministic naming, structure, and documentation conventions so CV pipeline, queue management, and MCU protocol code remain consistent and reviewable.

## Inputs / Outputs
- **Inputs**
  - Existing contributor guidance from `agents.md`.
  - Module boundaries from `architecture.md` and `filetree.md`.
- **Outputs**
  - Stable authoring rules for code, docs, configs, contracts, and protocol-facing symbols.

## States
- Naming conformance state: `compliant | non_compliant`.
- Contract naming state for schema/config artifacts: `canonical | drifted`.

## Dependencies
- `agents.md` deterministic naming section.
- `protocol.md` canonical command and frame terminology.
- `threading_model.md` shared state naming (`mode`, `queue_depth`, `scheduler_state`, `busy_flag`).
- Existing project layout under `src/coloursorter/*`, `configs/*`, `contracts/*`.

## Key Behaviors / Invariants
- Use snake_case for Python identifiers, module names, and non-protocol fields.
- Preserve canonical protocol terms exactly where required (`SCHED`, `SAFE`, `ACK`, `NACK`, `frame`, `queue`, `triggers`).
- Keep config and contract filenames canonical and stable.
- Public module boundaries should expose explicit typed inputs/outputs at pipeline stages.
- Documentation terms should align with CV pipeline and MCU wire contract vocabulary.
- When both representations appear, distinguish scheduler projection (`SCHED:<lane>:<position_mm>`) from transport frame (`<SCHED|lane|trigger_mm>`).

## Cross-layer Dependency Notes
- `testing_strategy.md` should enforce naming and protocol constant usage via lint/tests.
- `data_model.md` should reuse exact field names for telemetry and state snapshots to avoid cross-surface drift.
- `deployment.md` logs and dashboards should keep identical state field names across bench and production.

## Performance / Concurrency Notes
- Inconsistent naming of queue/scheduler fields can cause incorrect telemetry joins across CLI/GUI.
- Style drift in protocol constants can create parsing mismatches and latent runtime errors.

## Open Questions (requires input)
- Should GUI object names follow module naming conventions or a separate Qt/UI naming policy?
- Required style conventions for cross-language integration boundaries (Python ↔ C++/ESP32).
- Required automated linting/style tools and pinned versions for CI enforcement.

## Conflicts / Missing Links
- No explicit guideline yet for thread-safe logging formats under concurrent producers.
