# OpenSpec v3 API and Observability Contract

This document defines the external API and observability surfaces for OpenSpec v3 deployments. It covers HMI controls, remote operations, telemetry streams, audit/event records, and the compatibility bridge to bench CSV telemetry.

## 1) Control plane API: REST endpoints and WebSocket channels

All endpoints are versioned under `/api/v3`. Unless otherwise noted, payloads are JSON (`application/json`) and timestamps are RFC 3339 UTC strings.

### 1.1 REST endpoints

#### System and health

| Method | Path | Purpose | Request body | Response shape |
|---|---|---|---|---|
| `GET` | `/api/v3/health/live` | Liveness probe for process availability. | None | `{ "status": "alive", "service": "coloursorter", "ts": "..." }` |
| `GET` | `/api/v3/health/ready` | Readiness probe for camera, scheduler, and actuator transport. | None | `{ "status": "ready\|degraded\|not_ready", "checks": { ... }, "ts": "..." }` |
| `GET` | `/api/v3/system/info` | Returns deployed version/build and active profile metadata. | None | `{ "api_version": "v3", "build": {...}, "profile": {...} }` |

#### HMI runtime controls

| Method | Path | Purpose | Request body | Response shape |
|---|---|---|---|---|
| `GET` | `/api/v3/runtime/state` | Read current runtime mode and interlock state. | None | `{ "mode": "idle\|run\|pause\|fault", "interlocks": [...], "last_transition_ts": "..." }` |
| `POST` | `/api/v3/runtime/start` | Transition from `idle`/`pause` to `run` if interlocks permit. | `{ "requested_by": "<operator_id>", "reason": "optional" }` | `{ "accepted": true, "mode": "run", "correlation_id": "..." }` |
| `POST` | `/api/v3/runtime/pause` | Pause sorter while preserving buffered state. | `{ "requested_by": "<operator_id>", "reason": "optional" }` | `{ "accepted": true, "mode": "pause", "correlation_id": "..." }` |
| `POST` | `/api/v3/runtime/stop` | Controlled stop and queue drain. | `{ "requested_by": "<operator_id>", "reason": "optional" }` | `{ "accepted": true, "mode": "idle", "correlation_id": "..." }` |
| `POST` | `/api/v3/runtime/reset_fault` | Attempts fault recovery and returns post-reset state. | `{ "requested_by": "<operator_id>", "fault_id": "optional" }` | `{ "accepted": true, "mode": "idle\|fault", "remaining_faults": [...] }` |

#### Configuration and calibration

| Method | Path | Purpose | Request body | Response shape |
|---|---|---|---|---|
| `GET` | `/api/v3/config/active` | Fetch active runtime configuration (redacted secrets). | None | `{ "config_version": "...", "config": {...}, "etag": "..." }` |
| `PUT` | `/api/v3/config/active` | Replace active config atomically. Supports dry-run validation. | `{ "config": {...}, "dry_run": false, "requested_by": "..." }` | `{ "accepted": true, "config_version": "...", "validation": {...} }` |
| `GET` | `/api/v3/calibration` | Read active calibration values and lineage. | None | `{ "calibration_id": "...", "updated_at": "...", "params": {...} }` |
| `PUT` | `/api/v3/calibration` | Update calibration with validation report. | `{ "params": {...}, "requested_by": "..." }` | `{ "accepted": true, "calibration_id": "...", "validation": {...} }` |

#### Remote operations and diagnostics

| Method | Path | Purpose | Request body | Response shape |
|---|---|---|---|---|
| `POST` | `/api/v3/ops/command` | Submit authenticated remote operation command. | `{ "command": "set_mode\|e_stop\|clear_queue\|sync_clock", "args": {...}, "requested_by": "..." }` | `{ "accepted": true, "command_id": "...", "correlation_id": "..." }` |
| `GET` | `/api/v3/ops/command/{command_id}` | Query status of submitted command. | None | `{ "command_id": "...", "state": "pending\|running\|succeeded\|failed", "result": {...} }` |
| `GET` | `/api/v3/ops/faults/active` | Retrieve active faults and severity. | None | `{ "faults": [{ "fault_code": "...", "severity": "warn\|error\|critical", "raised_at": "..." }] }` |
| `GET` | `/api/v3/ops/audit` | Paginated audit log query for operations. | Query: `from`, `to`, `limit`, `cursor`, `actor`, `event_type` | `{ "events": [...], "next_cursor": "..." }` |

### 1.2 WebSocket channels

WebSocket base URL: `/ws/v3`. Clients MUST authenticate before subscribing.

| Channel | Direction | Semantics | QoS/ordering |
|---|---|---|---|
| `/ws/v3/runtime` | Server -> client | Runtime state transitions, interlocks, and fault state deltas for HMI. | Ordered per connection; latest snapshot sent on subscribe. |
| `/ws/v3/telemetry` | Server -> client | KPI and throughput telemetry updates (1 Hz default; burst on state change). | At-least-once; messages include monotonic `seq`. |
| `/ws/v3/events` | Server -> client | Detection/decision/actuation event stream with correlation IDs. | Best effort stream with replay token support. |
| `/ws/v3/ops` | Bi-directional | Remote command dispatch, ACK/NACK, and completion events. | Request/response over shared channel keyed by `command_id`. |

WebSocket message envelope:

```json
{
  "topic": "runtime.state.changed",
  "version": "3.0",
  "seq": 40219,
  "ts": "2026-01-03T10:15:21.284Z",
  "correlation_id": "a6d2f6bc-7c42-4a02-9f3c-e71ef71eaf7f",
  "payload": {}
}
```

## 2) Telemetry topic/event model

Telemetry topics use the namespace `v3.telemetry.<domain>.<metric>`. Each telemetry event MUST include:

- `topic`
- `version`
- `ts`
- `source` (`hmi`, `runtime`, `scheduler`, `actuator`, `bench`)
- `window` (`1s`, `10s`, `60s`, `lifetime`)
- `value` (numeric)
- `unit` (`items_s`, `ms`, `count`, `ratio`, `percent`)
- Optional dimensions (`lane_index`, `mode`, `fault_code`)

### 2.1 Required KPI topics

| KPI | Topic | Type | Definition |
|---|---|---|---|
| Throughput | `v3.telemetry.throughput.items_per_second` | Gauge | Items classified per second over declared `window`. |
| Uptime | `v3.telemetry.uptime.seconds` | Counter | Monotonic runtime uptime in seconds since last cold start. |
| Reject counts | `v3.telemetry.reject.count` | Counter | Total rejected items; dimensional by `rejection_reason` and optional `lane_index`. |
| Fault counts | `v3.telemetry.fault.count` | Counter | Total fault occurrences; dimensional by `fault_code` and `severity`. |
| End-to-end latency | `v3.telemetry.latency.e2e_ms` | Histogram sample | Detection-to-actuation elapsed time. |
| Decision latency | `v3.telemetry.latency.decision_ms` | Histogram sample | Inference + rules decision stage elapsed time. |
| Schedule latency | `v3.telemetry.latency.schedule_ms` | Histogram sample | Queue/scheduling stage elapsed time. |
| Transport latency | `v3.telemetry.latency.transport_ms` | Histogram sample | Command dispatch/transport elapsed time. |

### 2.2 Aggregation semantics

- Counters are cumulative and reset only on process restart; reset MUST emit `counter_reset=true`.
- Gauges represent the most recent computed value.
- Histogram samples MAY be emitted raw per cycle and aggregated server-side into P50/P95/P99 rollups.
- Rollup topics use `v3.telemetry.rollup.<metric>.p50|p95|p99` and include `window`.

## 3) Event and audit log schema with correlation IDs

A single `correlation_id` MUST follow an item lifecycle across:
1. Detection event
2. Decision event
3. Actuation event

A `causation_id` links child events to immediate parent events for branching workflows.

### 3.1 Canonical event schema

```json
{
  "event_id": "01J3MSKFFY2B7QTMX6A24F5J8H",
  "event_type": "detection.created|decision.made|actuation.commanded|actuation.ack|fault.raised|runtime.state_changed",
  "version": "3.0",
  "ts": "2026-01-03T10:15:21.284Z",
  "correlation_id": "a6d2f6bc-7c42-4a02-9f3c-e71ef71eaf7f",
  "causation_id": "01J3MSK8W3Q0TBP7H6K0R8R4W2",
  "trace_id": "2f53f66f1dd84ceaaea75613c57af7e2",
  "span_id": "e3437a9d85e9ca41",
  "actor": {
    "type": "system|operator|remote_client",
    "id": "runtime|op_123|svc_remote"
  },
  "asset": {
    "line_id": "line_a",
    "lane_index": 2
  },
  "payload": {}
}
```

### 3.2 Audit log schema

Audit records are append-only and MUST capture operator/remote intent and system outcome.

Required fields:

- `audit_id`
- `ts`
- `actor_id`
- `actor_type`
- `action`
- `target`
- `request_payload_hash`
- `result` (`accepted`, `rejected`, `failed`)
- `result_code`
- `correlation_id`
- `source_ip` (remote actions)

Retention recommendation:

- Hot storage: 30 days queryable.
- Cold archive: 13 months minimum for compliance and RCA.

## 4) Backward compatibility to bench CSV telemetry

This section maps OpenSpec v3 events/topics to legacy bench CSV fields from `docs/openspec/v3/telemetry_schema.md`.

| Existing bench CSV field | v3 topic/event mapping | Notes |
|---|---|---|
| `frame_timestamp` | `detection.created.ts` | Detection timestamp origin. |
| `trigger_generation_timestamp` | `decision.made.payload.trigger_generation_ts` | Preserves encoder-anchored scheduling baseline. |
| `trigger_timestamp` | `actuation.commanded.payload.trigger_ts` | Projected actuation time. |
| `trigger_mm` | `actuation.commanded.payload.trigger_mm` | Physical target distance. |
| `lane_index` | `asset.lane_index` + telemetry dimension `lane_index` | Shared dimension across events and KPI topics. |
| `rejection_reason` | `decision.made.payload.rejection_reason` + `v3.telemetry.reject.count{rejection_reason=*}` | Enables event-level and aggregate analysis. |
| `belt_speed_mm_s` | `decision.made.payload.belt_speed_mm_s` and optional topic `v3.telemetry.transport.belt_speed_mm_s` | Optional continuous telemetry topic. |
| `queue_depth` | `decision.made.payload.queue_depth` + `v3.telemetry.scheduler.queue_depth` | Gauge semantics in topic form. |
| `scheduler_state` | `runtime.state.changed.payload.scheduler_state` | Modeled as state transition events. |
| `mode` | `runtime.state.changed.payload.mode` + telemetry dimension `mode` | Backward-compatible operating mode visibility. |
| `ingest_latency_ms` | `v3.telemetry.latency.ingest_ms` | Existing non-breaking field promoted to topic. |
| `decision_latency_ms` | `v3.telemetry.latency.decision_ms` | Direct mapping. |
| `schedule_latency_ms` | `v3.telemetry.latency.schedule_ms` | Direct mapping. |
| `transport_latency_ms` | `v3.telemetry.latency.transport_ms` | Direct mapping. |
| `cycle_latency_ms` | `v3.telemetry.latency.e2e_ms` | Renamed to explicit end-to-end metric. |
| `nack_code` | `actuation.ack.payload.nack_code` | Event-first diagnostics. |
| `nack_detail` | `actuation.ack.payload.nack_detail` | Event-first diagnostics. |

Compatibility requirements:

- Producers MAY emit both legacy CSV fields and v3 topics/events during transition.
- Field-level parity checks SHOULD run in bench CI to ensure no metric drift.
- Consumers relying on CSV MUST be supported through the deprecation horizon in Section 5.

## 5) Versioning and deprecation policy

### 5.1 Versioning model

- API and topic contracts follow semantic versioning at major/minor granularity (`3.x`).
- Breaking changes (rename/remove/type-change) require a new major (`v4`) endpoint/topic namespace.
- Non-breaking additions (new optional fields/topics) increment minor version and MUST default safely.

### 5.2 Field lifecycle states

Each API field and telemetry topic has one lifecycle state:

- `active`: Fully supported for new integrations.
- `deprecated`: Supported but scheduled for removal; replacement is documented.
- `sunset`: Read-only compatibility mode, no new writes.
- `removed`: No longer emitted/accepted in the current major.

### 5.3 Deprecation guarantees

- Minimum deprecation window: 2 minor releases OR 6 months, whichever is longer.
- Deprecations MUST include:
  - Replacement field/topic
  - First version marked deprecated
  - Planned removal version/date
- REST responses SHOULD include deprecation metadata when deprecated fields are returned:
  - Header: `Deprecation: true`
  - Header: `Sunset: <http-date>`
  - Header: `Link: <replacement-doc-url>; rel="successor-version"`
- Telemetry topics SHOULD emit a companion annotation event:
  - `v3.telemetry.meta.deprecation_notice`

### 5.4 Compatibility test expectations

- Contract tests MUST validate required fields for `/api/v3` and all required KPI topics.
- Migration tests MUST assert equivalence between legacy bench CSV exports and v3 event/topic projections for shared metrics.
- Removal of deprecated fields/topics is blocked unless deprecation window and migration tests both pass.
