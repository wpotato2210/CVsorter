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

## States
- Trust state: `normal | suspicious | restricted`.
- Mode safety state: `AUTO | MANUAL | SAFE` with SAFE as protective state.
- Abuse detection counters: malformed frame rate, NACK burst rate, retry exhaustion count.

## Dependencies
- `protocol.md` frame grammar, command whitelist, NACK behavior.
- `error_model.md` escalation and recovery semantics.
- Deployment/runtime controls for process and device access.

## Key Behaviors / Invariants
- Only known commands are accepted; unknown commands return canonical NACK.
- Frame payload must reject delimiter/control injection (`<`, `>`, `|`).
- Mode transition policy must enforce `SAFE -> AUTO` prohibition.
- Repeated malformed frame bursts should trigger throttling and/or SAFE mode escalation.
- Queue reset and mode controls should be restricted to trusted operator/control paths.

## Performance / Concurrency Risks
- Excessive validation logging on malformed frame floods can degrade throughput.
- Shared counters without synchronization can undercount abuse in concurrent handlers.
- Throttling policies can interact poorly with retry backoff and create starvation.

## Integration Points
- Protocol parser and serial transport ingress.
- State/mode manager and scheduler queue controls.
- Deployment scripts/service configuration for permission hardening.

## Conflicts / Missing Links
- Authentication/authorization mechanism for command origin is not defined.
- No explicit secret or credential management guidance exists for production deployments.
