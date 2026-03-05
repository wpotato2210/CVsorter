# Gap Analysis Task Bundles (Condensed)

This plan safely consolidates remediation into **2 execution tasks** while preserving timing, safety, and contract intent.

## Task 1 — Contract & Safety Baseline
**Goal:** lock hard requirements and control-plane safety before implementation changes.

**Scope**
- Promote `openspec.md` to normative source of truth.
- Align `constraints.md`, `architecture.md`, `state_model.md`, `protocol.md`, and `security_model.md`.
- Define authenticated command requirements and heartbeat/watchdog escalation semantics.
- Standardize units and physical parameters from config-owned definitions.

**Mandatory constants/fields**
- `fps_target=100`
- `max_latency_ms<=15`
- `max_actuator_pulse_ms<=1`
- `queue_depth=8`
- `heartbeat_period_ms<=50`
- `heartbeat_timeout_ms<=150`
- states include `ESTOP_ACTIVE`, `SAFE_LATCH`
- timing variables: `frame_timestamp_ms`, `pipeline_latency_ms`, `trigger_offset_ms`, `actuation_delay_ms`

**Exit criteria**
- All listed docs use the same numeric bounds and state names.
- Motion-capable commands require auth + anti-replay fields.
- E-STOP and latch transitions are explicit and unambiguous.

## Task 2 — Deterministic Pipeline Delivery + Evidence
**Goal:** ship deterministic runtime behavior with verifiable contracts and operator readiness.

**Scope**
- Implement/align requested runtime modules only:
  - `preprocess | dataset | model | train | eval | infer | scheduler | actuator_iface | config`
- Enforce runtime assertions:
  - image shape `(H,W,3)`
  - tensor shape `(B,C,H,W)`
  - device match
  - dataset nonempty
- Ensure all physical constants are loaded from `src/coloursorter/config/*` (no inline physical constants).
- Publish canonical telemetry/config schemas and acceptance tests.
- Update operator/deployment SOPs and close missing artifact traceability.

**Exit criteria**
- Deterministic I/O contracts are documented for each requested module.
- Acceptance evidence includes latency, throughput, and E-STOP response thresholds.
- Operator go/no-go and reset authority workflow are documented.

## Dependency order
1. Task 1 (contracts and safety semantics)
2. Task 2 (implementation and validation)

This order minimizes rework and prevents implementation drift against unresolved safety/realtime requirements.
