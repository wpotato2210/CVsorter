# error_model.md

## Purpose
Define canonical error categories, NACK mappings, and recovery behavior for CV pipeline, scheduler queue, and MCU transport interactions.

## Inputs / Outputs
- **Inputs**
  - Parser/validation failures from incoming protocol frame handling.
  - Queue and scheduler failures from `SCHED` admission and dispatch.
  - Runtime mode/state violations and transport timeout events.
- **Outputs**
  - Standardized `<NACK|code|detail>` responses.
  - Deterministic local recovery actions (drop frame, clear queue, retry, enter SAFE mode).
  - Operator-visible diagnostics for CLI/GUI telemetry.

## States
- Error severity: `recoverable | degraded | fail_safe`.
- Recovery state: `retrying | rejected | safe_halt`.
- Transport retry state: attempt index `0..3`.

## Dependencies
- `protocol.md` canonical NACK codes (1..8) and retry policy.
- `state_model.md` for mode/scheduler transition side effects.
- `security_model.md` for suspicious/flood escalation behavior.
- Scheduler and serial_interface runtime modules.

## Key Behaviors / Invariants
- Every rejected command/frame must map to one canonical NACK code and detail.
- `BUSY`, `QUEUE_FULL`, and malformed frame outcomes must be explicit and non-ambiguous.
- Retry is bounded (timeout `100 ms`, max retries `3`) and must not duplicate semantic side effects.
- Invalid mode transitions preserve current mode and queue safety invariants.
- Escalation path for repeated transport failures should prefer SAFE mode over undefined operation.

## Cross-layer dependency notes
- `constraints.md` validation limits are upstream of most recoverable error paths.
- `deployment.md` should define production-safe handling and alerting thresholds for error bursts.
- `testing_strategy.md` must pin code/detail mappings and recovery transitions as regression checks.

## Open questions (requires input)
- Full internal-exception → external NACK mapping table is not enumerated.
- Bench vs production differences for error propagation/reporting are not explicitly documented.
- Whether SAFE mode is mandatory automatic action for all critical faults (or policy-driven) is unspecified.

## Performance / Concurrency Risks
- Concurrent requesters can induce conflicting retries and duplicate `SCHED` submissions without host-side serialization.
- Overly aggressive retry timing can worsen link congestion and increase BUSY/NACK rates.
- Error fan-out to GUI/CLI can lag under burst failures if telemetry queueing is unbounded.

## Integration Points
- Protocol parser and encoder in `src/coloursorter/protocol/*` and `src/coloursorter/serial_interface/*`.
- Scheduler queue admission and reset pathways.
- Bench telemetry aggregation and operator alerts.

## Conflicts / Missing Links
- No documented dead-letter strategy for repeatedly failing triggers.
