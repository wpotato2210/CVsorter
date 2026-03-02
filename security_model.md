# security_model.md

## Purpose
Define practical security controls for protocol parsing, mode protection, and operational safeguards so malformed or abusive traffic cannot compromise queue safety or trigger integrity.

## Inputs / Outputs
- **Inputs**
  - Incoming ASCII frame traffic at MCU protocol boundary.
  - Runtime mode control requests and queue operations.
  - Deployment environment controls (host access, serial device permissions).
- **Outputs**
  - Parser hardening and input validation policy.
  - SAFE mode enforcement policy under suspicious/fault conditions.
  - Auditable security-relevant event logging requirements.

## Terminology Alignment (protocol + architecture)
- Security controls preserve protocol frame grammar and command whitelist semantics; they do not redefine command behavior.
- Security event provenance uses architecture stage labels so abuse can be localized (ingest, parser, scheduler admission, transport).

## States
- Trust state: `normal | suspicious | restricted`.
- Mode safety state: `AUTO | MANUAL | SAFE` with SAFE as protective state.
- Abuse detection counters: malformed frame rate, NACK burst rate, retry exhaustion count.

## Dependencies
- `protocol.md` frame grammar, command whitelist, NACK behavior.
- `error_model.md` escalation and recovery semantics.
- `state_model.md` mode restrictions and queue-reset implications.
- Deployment/runtime controls for process and device access.

## Key Behaviors / Invariants
- Only known commands are accepted; unknown commands return canonical NACK.
- Frame payload must reject delimiter/control injection (`<`, `>`, `|`).
- Mode transition policy must enforce `SAFE -> AUTO` prohibition.
- Repeated malformed frame bursts should trigger throttling and/or SAFE mode escalation.
- Queue reset and mode controls should be restricted to trusted operator/control paths.

## Cross-layer Dependency Notes
- `threading_model.md` must define synchronized abuse counters under concurrent handlers.
- `deployment.md` must implement host hardening (device permissions, service account scope, log retention).
- `testing_strategy.md` should include malformed-frame flood and retry-abuse scenarios.
- `data_model.md` should define retained security-event fields needed for auditability.

## Performance / Concurrency Notes
- Excessive validation logging on malformed frame floods can degrade throughput.
- Shared counters without synchronization can undercount abuse in concurrent handlers.
- Throttling policies can interact poorly with retry backoff and create starvation.

## Open Questions (requires input)
- Authentication/authorization model for command producers (none, shared secret, RBAC, physical link trust).
- Exact response policy to malformed-frame floods (drop, throttle, temporary lockout, SAFE transition).
- Whether SAFE mode and communications lockdown are coupled or independently controlled.
- Throttle policy ownership and limits (per command producer, per transport link, or global).

## Conflicts / Missing Links
- No explicit secret or credential management guidance exists for production deployments.
