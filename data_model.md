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

## Key Behaviors / Invariants
- Lane and trigger fields remain strongly typed and range-validated before serialization.
- Protocol emission uses canonical `SCHED:<lane>:<position_mm>` projection from structured scheduler data.
- ACK/NACK telemetry records preserve code/detail and correlation to originating frame/trigger where available.
- Schema evolution must be additive or accompanied by explicit migration notes.

## Performance / Concurrency Risks
- High-frequency frame telemetry can create storage pressure without retention limits.
- Concurrent telemetry writes can reorder related queue/ACK events unless sequence IDs are used.
- Large object payloads can increase serialization overhead and jitter in scheduler loops.

## Integration Points
- CV pipeline model types and deploy orchestration outputs.
- Scheduler output and serial protocol adapter.
- Bench CLI/GUI telemetry consumers and reporting tools.

## Conflicts / Missing Links
- Canonical field-level schemas for internal telemetry objects are not yet documented.
- Data retention and archival policy is currently unspecified.
