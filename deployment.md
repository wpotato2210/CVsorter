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

## Terminology Alignment (protocol + architecture)
- Operational telemetry must retain protocol field names and enum values (`mode`, `queue_depth`, `scheduler_state`, `IDLE|ACTIVE`, ACK/NACK details).
- Deployment runbooks must refer to architecture stages by canonical names (preprocess, calibration, deploy, eval, scheduler, serial transport).

## States
- Deployment stage: `bench | staging | production`.
- Service lifecycle: `provisioned | running | degraded | halted_safe`.
- Connectivity state: `mcu_connected | mcu_unavailable | retrying`.

## Dependencies
- `architecture.md` runtime component map.
- `protocol.md` timeout/retry and mode transition behavior.
- `security_model.md` controls for parser hardening and host access.
- `constraints.md` and `state_model.md` invariants that must remain unchanged across environments.

## Key Behaviors / Invariants
- Startup validates contracts/config compatibility before accepting frame stream input.
- Runtime exposes mode, queue depth, scheduler state, and transport health telemetry.
- SAFE mode is always available as operator-visible and scriptable fail-safe action.
- Deployment-specific config overrides must not change protocol contract semantics.
- Recovery after transport loss must preserve deterministic queue/state behavior.

## Cross-layer Dependency Notes
- `testing_strategy.md` defines pre-promotion checks that should gate bench -> staging -> production.
- `error_model.md` and `security_model.md` define escalation pathways requiring operator runbook entries.
- `data_model.md` defines telemetry outputs needed for operational observability and rollback diagnostics.

## Performance / Concurrency Notes
- Production serial jitter can exceed bench assumptions and increase trigger lag.
- Restart races can duplicate in-flight triggers if queue checkpoint strategy is absent.

## Open Questions (requires input)
- **Authoritative queue sizing:** fixed protocol default (`8`) vs environment-specific overrides, and who approves overrides.
- **Timing/servo constraints:** production MCU/servo timing budgets and explicit mapping from bench timings to production tolerances.
- **Execution model in production:** single-process event loop vs multi-worker topology and ownership of queue admission ordering.
- Rollout/rollback lifecycle procedures, maintenance windows, and release ownership model.
- SAFE mode enforcement differences (if any) between staging and production.

## Conflicts / Missing Links
- Target deployment platform matrix (OS/hardware/serial adapters) is not documented.
- No formal release gate currently links bench pass criteria to production promotion.
