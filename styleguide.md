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
- `architecture.md` module boundaries and CV pipeline labels.
- Existing project layout under `src/coloursorter/*`, `configs/*`, `contracts/*`.

## Key Behaviors / Invariants
- Use snake_case for Python identifiers, module names, and non-protocol fields.
- Preserve canonical protocol terms exactly where required (`SCHED`, `SAFE`, `ACK`, `NACK`, `frame`, `queue`, `triggers`).
- Keep config and contract filenames canonical and stable.
- Public module boundaries should expose explicit typed inputs/outputs at pipeline stages.
- Documentation terms should align with CV pipeline and MCU wire contract vocabulary.

## Cross-layer dependency notes
- `constraints.md` and `state_model.md` depend on stable names for mode/queue/scheduler telemetry fields.
- `data_model.md` schema naming depends on shared canonical field/contract names.
- `testing_strategy.md` test IDs/assertions should mirror protocol and state term spelling exactly.

## Open questions (requires input)
- GUI object naming convention is not explicit (should GUI IDs follow module naming conventions or UI-framework defaults?).
- Cross-language style guidance (Python host ↔ C++/ESP32 firmware naming/types/error conventions) is undefined.
- Required automated style/lint enforcement matrix (ruff/black/mypy/clang-format/etc.) is not declared.

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
