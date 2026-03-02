# deployment.md

## Purpose
Define deployment topology and operational procedures that carry bench-validated CV pipeline and queue behavior into production-connected MCU environments safely.

## Inputs / Outputs
- **Inputs**
  - Runtime configs (`default_config`, bench/runtime geometry/calibration).
  - Protocol retry and mode/queue safety policy.
  - Host environment parameters (serial port, process manager, logging sink).
- **Outputs**
  - Repeatable deployment profile for bench and production variants.
  - Operational runbook for startup, monitoring, SAFE mode intervention, and recovery.

## States
- Deployment stage: `bench | staging | production`.
- Service lifecycle: `provisioned | running | degraded | halted_safe`.
- Connectivity state: `mcu_connected | mcu_unavailable | retrying`.

## Dependencies
- `architecture.md` runtime component map.
- `protocol.md` timeout/retry and mode transition behavior.
- `threading_model.md` for runtime serialization assumptions.
- `security_model.md` controls for parser hardening and host access.

## Key Behaviors / Invariants
- Startup validates contracts/config compatibility before accepting frame stream input.
- Runtime exposes mode, queue depth, scheduler state, and transport health telemetry.
- SAFE mode is always available as operator-visible and scriptable fail-safe action.
- Deployment-specific config overrides must not change protocol contract semantics.
- Recovery after transport loss must preserve deterministic queue/state behavior.

## Cross-layer dependency notes
- Bench promotion to staging/production should be gated by `testing_strategy.md` criteria and protocol/state conformance.
- Error escalation behavior must remain aligned with `error_model.md` and `security_model.md`.
- Persisted telemetry expectations should match `data_model.md` schema/retention choices.

## Open questions (requires input)
- Production MCU timing budgets and trigger mapping tolerances relative to bench are not fully defined.
- Rollback/maintenance lifecycle (release approval, canary strategy, rollback criteria) is not documented.
- SAFE mode enforcement differences across staging vs production are unspecified.

## Performance / Concurrency Risks
- Production transport latency variance can exceed bench assumptions and stress retry policy.
- Resource-constrained hosts may reduce frame throughput and increase trigger lag.
- Restart races can duplicate in-flight triggers if queue checkpoint strategy is absent.

## Integration Points
- CLI/GUI bench tooling for pre-prod validation.
- Process manager/service wrapper and environment configuration.
- Monitoring/alerting hooks for NACK bursts, BUSY rates, and SAFE mode entries.

## Conflicts / Missing Links
- Target deployment platform matrix (OS/hardware/serial adapters) is not documented.
- No formal release gate currently links bench pass criteria to production promotion.
