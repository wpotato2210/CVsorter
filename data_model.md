# data_model.md

## Purpose
Define canonical runtime and persisted data entities for frame processing, scheduling decisions, queue state, and protocol telemetry across bench and production usage.

## Inputs / Outputs
- **Inputs**
  - Frame metadata and object detections.
  - Calibration/lane geometry config data.
  - Protocol command/response frames and scheduler events.
- **Outputs**
  - Normalized `DecisionPayload` and scheduled trigger records.
  - Persistable telemetry/event records for mode, queue, and transport outcomes.
  - Version-aware schema alignment with `contracts/*.json` and `data/manifest.json`.

## States
- Data schema version state: `manifest_version` + contract revision.
- Runtime object lifecycle: `ingested -> enriched -> evaluated -> scheduled -> transmitted`.
- Trigger record state: `queued | sent | acked | failed`.

## Dependencies
- `contracts/frame_schema.json`, `contracts/sched_schema.json`, `contracts/mcu_response_schema.json`.
- `data/manifest.json`.
- Model/deploy/scheduler/protocol runtime modules.
- `state_model.md` and `error_model.md` state/error taxonomies for telemetry.

## Key Behaviors / Invariants
- Lane and trigger fields remain strongly typed and range-validated before serialization.
- Scheduler data projects to canonical `SCHED:<lane>:<position_mm>` and then encodes to protocol frame format for transport.
- ACK/NACK telemetry records preserve code/detail and correlation to originating frame/trigger where available.
- Schema evolution must be additive or accompanied by explicit migration notes.

## Cross-layer Dependency Notes
- `constraints.md` sets authoritative numeric ranges consumed by schema and validators.
- `testing_strategy.md` should include schema compatibility and migration regression tests.
- `deployment.md` determines telemetry persistence, retention, and export pipeline expectations.

## Performance / Concurrency Notes
- High-frequency frame telemetry can create storage pressure without retention limits.
- Concurrent telemetry writes can reorder related queue/ACK events unless sequence IDs are used.
- Large object payloads can increase serialization overhead and jitter in scheduler loops.

## Open Questions (requires input)
- Canonical schema definitions for telemetry, queue event logs, and deployment manifests.
- Persisted-state expectations: full frame/trigger history vs summary aggregates only.
- Required schema versioning/evolution policy (semantic versioning, compatibility window, migration process).

## Conflicts / Missing Links
- Canonical field-level schemas for internal telemetry objects are not yet documented.
- Data retention and archival policy is currently unspecified.
