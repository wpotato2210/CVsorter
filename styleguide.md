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
- Existing project layout under `src/coloursorter/*`, `configs/*`, `contracts/*`.

## Key Behaviors / Invariants
- Use snake_case for Python identifiers, module names, and non-protocol fields.
- Preserve canonical protocol terms exactly where required (`SCHED`, `SAFE`, `ACK`, `NACK`, `frame`, `queue`, `triggers`).
- Keep config and contract filenames canonical and stable.
- Public module boundaries should expose explicit typed inputs/outputs at pipeline stages.
- Documentation terms should align with CV pipeline and MCU wire contract vocabulary.

## Performance / Concurrency Risks
- Inconsistent naming of queue/scheduler fields can cause incorrect telemetry joins across CLI/GUI.
- Style drift in protocol constants can create parsing mismatches and latent runtime errors.

## Integration Points
- Code review and CI lint/type checks.
- `tests/` assertions that reference protocol constants and scheduler states.
- Bench CLI/GUI telemetry labels and state displays.

## Conflicts / Missing Links
- Formatting/lint toolchain versions are not pinned in this document.
- No explicit guideline yet for thread-safe logging formats under concurrent producers.
