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

## Terminology Alignment (protocol + architecture)
- External failures must map to protocol-defined NACK detail labels (`UNKNOWN_COMMAND`, `QUEUE_FULL`, `BUSY`, `MALFORMED_FRAME`, etc.).
- Internal error origin tags should match architecture stages (preprocess/calibration/deploy/eval/scheduler/transport) for triage.

## States
- Error severity: `recoverable | degraded | fail_safe`.
- Recovery state: `retrying | rejected | safe_halt`.
- Transport retry state: attempt index `0..3`.

## Dependencies
- `protocol.md` canonical NACK codes (1..8) and retry policy.
- `state_model.md` mode/queue transition side effects.
- `threading_model.md` serialization assumptions preventing duplicate side effects.
- Scheduler and serial_interface runtime modules.

## Key Behaviors / Invariants
- Every rejected command/frame must map to one canonical NACK code and detail.
- `BUSY`, `QUEUE_FULL`, and malformed frame outcomes must be explicit and non-ambiguous.
- Retry is bounded (timeout `100 ms`, max retries `3`) and must not duplicate semantic side effects.
- Invalid mode transitions preserve current mode and queue safety invariants.
- Escalation path for repeated transport failures should prefer SAFE mode over undefined operation.

## Cross-layer Dependency Notes
- `constraints.md` defines input/range violations that should map to `ARG_*` NACKs.
- `security_model.md` may escalate malformed/flood behavior into SAFE mode or throttling.
- `deployment.md` should surface operator runbooks for `degraded` and `fail_safe` states.
- `data_model.md` should preserve stable error fields for correlation and audit trails.

## Performance / Concurrency Notes
- Concurrent requesters can induce conflicting retries and duplicate `SCHED` submissions without host-side serialization.
- Overly aggressive retry timing can worsen link congestion and increase BUSY/NACK rates.
- Error fan-out to GUI/CLI can lag under burst failures if telemetry queueing is unbounded.

## Open Questions (requires input)
- Full canonical list of error codes/triggers/recovery actions beyond protocol-level NACK set.
- Differences in error propagation/reporting between bench simulations and production deployments.
- Whether critical classes of failures must automatically invoke SAFE mode.
- Whether repeated BUSY/QUEUE_FULL should trigger adaptive throttling or hard rejection windows.

## Conflicts / Missing Links
- Canonical mapping from non-protocol internal exceptions to external NACK codes is not yet enumerated.
- No documented dead-letter strategy for repeatedly failing triggers.
