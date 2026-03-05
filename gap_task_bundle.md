# Gap Analysis Task Bundles

This document consolidates the previously enumerated remediation actions into a smaller set of safe execution tracks while preserving timing, safety, and contract intent.

## Bundle 1 — Normative Safety + Realtime Contracts
**Goal:** establish one source of truth for hard requirements.

**Includes:**
- Promote `openspec.md` to normative contract.
- Align `constraints.md`, `state_model.md`, `architecture.md` to same numeric limits and state names.
- Add explicit units and acceptance thresholds (`ms`, `us`, `mm`, `kPa`).

**Exit criteria:**
- Required constants explicitly documented: `fps_target=100`, `max_latency_ms<=15`, `max_actuator_pulse_ms<=1`, `queue_depth=8`.
- State model includes `ESTOP_ACTIVE` and `SAFE_LATCH` transitions.

## Bundle 2 — Secure Control Plane + Deterministic Runtime
**Goal:** prevent unsafe motion commands and timing drift in execution.

**Includes:**
- Upgrade protocol framing with anti-replay authentication semantics.
- Define heartbeat period/timeout and escalation to `DEGRADED`/`SAFE_LATCH`.
- Specify deterministic worker architecture (Capture/Decision/Actuation) with bounded handoff policies and watchdog behavior.

**Exit criteria:**
- Motion-capable commands require authentication.
- Heartbeat and watchdog thresholds are numerically specified and shared across protocol/threading docs.
- Queue handoff and backpressure behavior are deterministic and documented.

## Bundle 3 — Schemas, Validation, and Acceptance Evidence
**Goal:** make contracts testable and auditable.

**Includes:**
- Publish canonical telemetry and runtime config schemas.
- Add/restore validator and latency/calibration tooling references.
- Extend test strategy with hard pass/fail thresholds for latency, throughput, and safety response.

**Exit criteria:**
- Versioned schema files exist and are referenced by docs.
- Acceptance tests include p99 latency and E-STOP response criteria.
- Validation workflow maps each test to a requirement ID.

## Bundle 4 — Operations Readiness + Traceability Closure
**Goal:** ensure safe field operation and complete artifact traceability.

**Includes:**
- Update operator SOP (`USER_MANUAL.md`, `QUICK_START.md`) with preflight, calibration tolerances, E-STOP drills, and reset authority.
- Harden deployment controls (authenticated command channel, auditability, telemetry retention/SLOs).
- Resolve missing MCU/HMI/tooling artifacts or document authoritative replacements.

**Exit criteria:**
- Go/no-go checklist required before `RUNNING` mode.
- Safety drill and reset workflow are explicit and role-gated.
- Filetree/docs identify safety/realtime critical artifacts and ownership.

## Safe sequencing
1. Bundle 1
2. Bundle 2
3. Bundle 3
4. Bundle 4

This order minimizes rework by setting requirements first, then implementation semantics, then evidence, then operationalization.
