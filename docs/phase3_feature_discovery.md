# Phase 3 High-Signal Feature Discovery

## Step 1 — Repository understanding

### What the system currently does
- Deterministic bench execution in replay/live modes with artifact generation (`summary.json`, `events.jsonl`, `telemetry.csv`).
- Runtime and bench flows already include configurable detection providers (`opencv_basic`, `opencv_calibrated`, `model_stub`) and transport backends (`mock`, `serial`, `esp32`).
- Runtime path includes startup diagnostics, frame freshness guarding, safety/latency budget integration, and trace logging.
- A large pytest suite exists across protocol, transport, safety gates, bench parity, runtime determinism, and phase-gated acceptance checks.

### What it does not yet do
- No implementation of the OpenSpec v3 external control-plane API (`/api/v3/...`) or WebSocket channels (`/ws/v3/...`) appears in `src/`.
- No production-facing service endpoint exists for remote runtime control, readiness/health probing, config/calibration mutation, command audit query, or event streaming.
- Existing runtime observability is file/artifact oriented, not API/topic oriented as specified in OpenSpec API & observability contracts.

### Intended but unfinished signals
- OpenSpec defines explicit REST + WebSocket contracts, telemetry topics, and audit/event schemas.
- Current implementation has deterministic runtime internals and logs needed to drive those surfaces, but lacks the serving layer that turns these into operator/remote workflows.

## Step 2 — System capability assessment

### Working features
- End-to-end deterministic bench pipeline (ingest -> detect -> decide -> schedule/transport) with scenario evaluation and artifacts.
- Protocol handling and host/firmware transport compatibility checks with broad test coverage.
- Live runtime loop with startup diagnostics, stale-frame protection, and timing trace logging.

### Partially implemented features
- GUI exists (bench app + integration stub), but the stub still uses placeholder/simulated behavior and random feedback.
- Observability data is present in bench/runtime artifacts but not exposed via OpenSpec API/topic interfaces.

### Missing capabilities for usable deployment workflow
- Remote/human operator control API for start/pause/stop/reset, fault views, and ops command handling.
- Service-level readiness/liveness endpoints for orchestration.
- Versioned event/telemetry stream transport (WebSocket) and queryable audit trail.

## Step 3 — Candidate Phase 3 improvements (3–5)

### Candidate A — Implement OpenSpec v3 runtime control-plane API + WebSocket bridge
- Impact: Very high. Unlocks practical HMI + remote operations and exposes existing runtime/telemetry capabilities through stable contracts.
- Complexity: Medium-high (service layer, state/authorization plumbing, event serialization, integration tests).
- Likely files/modules:
  - New: `src/coloursorter/api/v3/*`
  - Integrate with: `src/coloursorter/runtime/live_runner.py`, `src/coloursorter/runtime/trace_logger.py`, `src/coloursorter/bench/evaluation.py`
  - Tests: new API contract + compatibility tests in `tests/`

### Candidate B — Replace GUI integration stub with deterministic runtime/transport adapter
- Impact: High for local operator UX; lower for external integration.
- Complexity: Medium.
- Likely files/modules:
  - `gui/bench_app/controller_integration_stub.py`
  - `gui/bench_app/controller.py`
  - tests in `tests/test_bench_controller_gui.py`

### Candidate C — Build calibration/profile management workflow (validate + activate)
- Impact: High for field setup quality and repeatability.
- Complexity: Medium.
- Likely files/modules:
  - `src/coloursorter/config/runtime.py`
  - `src/coloursorter/deploy/detection.py`
  - new tooling in `tools/` + tests

### Candidate D — Hardware readiness evidence automation
- Impact: Medium-high for release confidence; lower direct operator value.
- Complexity: Medium.
- Likely files/modules:
  - `tools/hardware_readiness_report.py`
  - `scripts/*` orchestration wrappers
  - bench/integration evidence tests

## Step 4 — Selected killer feature

### Feature
Implement the **OpenSpec v3 runtime control-plane service** (REST + WebSocket) that wraps existing deterministic runtime components.

### Why this is highest value
- It converts the project from primarily bench/tooling execution into a remotely operable system.
- It is directly implied by OpenSpec and currently absent.
- It multiplies value of already-built internals (runtime state, telemetry, artifacts, protocol handling) without requiring architecture-contract changes.

### Dependencies
- Deterministic runtime state accessors and command execution facade.
- Event envelope/telemetry serializers.
- API framework dependency already present or added in reproducible offline-compatible way.

### Workflow improvement
- Before: users run CLI/GUI locally and inspect files manually.
- After: users can programmatically health-check, start/stop, inspect faults, apply config/calibration, submit ops commands, and subscribe to runtime/telemetry/events in real time.

## Step 5 — Concrete implementation plan

### Modules to modify
- `src/coloursorter/runtime/live_runner.py`
  - expose stable state snapshot + command methods used by API layer.
- `src/coloursorter/runtime/trace_logger.py`
  - optional event envelope helpers for API streaming consistency.

### New files to add
- `src/coloursorter/api/v3/app.py` (service wiring)
- `src/coloursorter/api/v3/models.py` (request/response schemas)
- `src/coloursorter/api/v3/runtime_routes.py`
- `src/coloursorter/api/v3/ops_routes.py`
- `src/coloursorter/api/v3/ws_routes.py`
- `tests/test_api_v3_runtime.py`
- `tests/test_api_v3_ops.py`
- `tests/test_api_v3_ws.py`

### APIs/interfaces to add
- REST:
  - `GET /api/v3/health/live`
  - `GET /api/v3/health/ready`
  - `GET /api/v3/runtime/state`
  - `POST /api/v3/runtime/start|pause|stop|reset_fault`
  - `GET/PUT /api/v3/config/active`
  - `GET/PUT /api/v3/calibration`
  - `POST /api/v3/ops/command`
  - `GET /api/v3/ops/command/{command_id}`
  - `GET /api/v3/ops/faults/active`
  - `GET /api/v3/ops/audit`
- WebSocket:
  - `/ws/v3/runtime`
  - `/ws/v3/telemetry`
  - `/ws/v3/events`
  - `/ws/v3/ops`

### Test coverage required
- Contract tests for endpoint shapes/status codes and deterministic payload ordering where required.
- Lifecycle tests for runtime transitions and invalid transitions.
- Compatibility tests mapping emitted telemetry/events to existing bench/runtime fields.
- Replayable deterministic tests for WebSocket sequence and correlation IDs.

## Step 6 — Minimal first implementation step

- Exact file to edit: `src/coloursorter/runtime/live_runner.py`
- Specific change:
  - add a read-only deterministic `runtime_state_snapshot()` method on `LiveRuntimeRunner` returning mode, diagnostics summary, last fault (if any), and monotonic timestamps needed by API `GET /api/v3/runtime/state`.
- Expected output/result:
  - API scaffolding can consume one stable runtime snapshot source immediately.
  - first API contract test can be added with a fake runner and no transport/camera dependency.
