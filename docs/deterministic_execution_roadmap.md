# Deterministic See-Decide-Trigger-Verify Roadmap (Repository-Truth)

- Assumption (single): "fully functioning" means parity between Python host path and MCU firmware path for the existing OpenSpec v3 command/ACK contract, with deterministic actuation and observable verification on every trigger.

## Phase 1 — Current State Audit

### 1) Module inventory (implemented vs stub vs missing)

| File / Module | Responsibility | Completeness % | Status |
|---|---|---:|---|
| `src/coloursorter/deploy/detection.py` | Detection providers (`opencv_basic`, `opencv_calibrated`, `model_stub`), preprocess normalization, provider contract checks | 85 | Implemented; deterministic provider outputs sorted by `object_id`; no hardware feedback coupling |
| `src/coloursorter/preprocess/lane_segmentation.py` | Lane geometry load + lane assignment | 90 | Implemented; strict lane count/boundary checks |
| `src/coloursorter/preprocess/lane_extraction.py` | Per-frame geometry scaling + alignment faulting | 85 | Implemented; degrades with explicit reason |
| `src/coloursorter/calibration/mapping.py` | Pixel-to-mm conversion + calibration hash validation | 95 | Implemented; deterministic hash gate |
| `src/coloursorter/eval/rules.py` | Reject/accept/unknown decision logic | 90 | Implemented; deterministic threshold mapping |
| `src/coloursorter/deploy/pipeline.py` | Orchestrates detect outputs -> lane/calibration -> decisions -> scheduled commands | 88 | Implemented; suppresses schedule on faults |
| `src/coloursorter/scheduler/output.py` | Scheduler command builder + lane/trigger bounds guard | 95 | Implemented; bounds validated |
| `src/coloursorter/serial_interface/serial_interface.py` | Packet frame serialize/parse/CRC + ACK/NACK token validation | 92 | Implemented; strict framing and schema-like validation |
| `src/coloursorter/bench/serial_transport.py` | Serial link state management (HELLO/HEARTBEAT/GET_STATE sync), retries, ACK mapping | 85 | Implemented host-side state machine; no physical actuator verification |
| `src/coloursorter/protocol/host.py` | OpenSpec host authority emulator (mode/state/queue/link transitions) | 88 | Implemented simulation authority |
| `src/coloursorter/ingest/boundary.py` | Ingest schema adaptation + bounded queue + deterministic drop policy | 90 | Implemented deterministic ingress boundary |
| `src/coloursorter/bench/runner.py` | End-to-end bench cycle, budget/fault handling, telemetry logs | 80 | Implemented but contains fallback-generated synthetic responses on send-budget breach |
| `src/coloursorter/runtime/live_runner.py` | Live loop orchestration (frame source, detector, pipeline, transport) | 78 | Implemented orchestration; no trigger-closed-loop verification |
| `firmware/mcu/src/scheduler.c` | MCU queue enqueue/dequeue/depth | 55 | Implemented queue primitive only |
| `firmware/mcu/src/main.c` | MCU init + watchdog kick loop | 30 | Stub-level control loop (no protocol execution, no actuator task) |
| `firmware/mcu/src/isr.c` | UART/tick ISR placeholders | 20 | Stub (UART byte shadow only; no parser/dispatcher wiring) |
| `firmware/mcu/src/watchdog.c` | Watchdog primitive state | 45 | Implemented primitive only |
| `firmware/mcu/src/brownout.c` | Brownout threshold primitive | 45 | Implemented primitive only |
| `contracts/frame_schema.json` | Ingest payload contract | 95 | Implemented + enforced by ingest adapter |
| `contracts/mcu_response_schema.json` | MCU ACK/NACK response schema | 90 | Implemented contract; parity tested |

### 2) Data-flow map (CV -> scheduler -> transport -> MCU -> actuator -> feedback)

| Stage | Producer | Artifact | Consumer | Deterministic guard |
|---|---|---|---|---|
| CV detect | `DetectionProvider.detect` | `list[ObjectDetection]` | `PipelineRunner.run` | Frame shape/dtype validation; output validation |
| Decide | `PipelineRunner.run` + `decision_outcome_for_object` | `DecisionPayload` | Scheduler builder and logs | Fault reason overrides to `unknown`; deterministic threshold checks |
| Schedule projection | `build_scheduled_command` | `ScheduledCommand(lane, position_mm)` | Transport | Lane/trigger bounds checks |
| Wire transport | `SerialMcuTransport._send_frame` | `<MSG|CMD|payload|CRC>` bytes | Host/MCU protocol peer | CRC32 frame validation + retries + strict parse |
| MCU queue | `OpenSpecV3Host._sched` (sim) / `firmware scheduler_enqueue` (firmware primitive) | queue depth/state mutation | Actuator dispatcher (missing in firmware) | Queue capacity checks in host sim and C queue primitive |
| Actuator command execution | Bench transport response mapping | `TransportResponse` + logs | Bench/live telemetry | Host/bench ACK mapping only; hardware actuation path incomplete |
| Feedback verification | Bench log + ACK fields | queue/mode/scheduler/link fields | Evaluation/artifacts | ACK-level verification exists; physical trigger confirmation missing |

### 3) Timing model summary (timestamp origin + ownership)

| Timestamp / Metric | Origin | Owner of truth | Notes |
|---|---|---|---|
| `FrameMetadata.timestamp_s` | frame source payload/capture | Frame source | Passed through pipeline without normalization |
| Cycle timers (`cycle_started`, stage latencies) | `time.perf_counter()` in runner/live | Host runtime process | Monotonic local host clock |
| Ingest queue timing (`enqueued_monotonic_s`, staleness) | `IngestBoundary.submit` (`perf_counter`) | Ingest boundary | Deterministic queue-age calculations |
| Serial round-trip (`round_trip_ms`) | `_send_frame` measured around write/read | Transport layer | Depends on serial I/O jitter |
| Trigger projection time | `VirtualEncoder.project_trigger_timestamp` | Bench runner | Model-based estimate, not sensor-verified trigger time |
| Link liveness | `time.monotonic()` heartbeat bookkeeping | Serial transport | Heartbeat-driven link state transitions |
| MCU runtime timebase | Tick ISR counter placeholder | Firmware (partial) | Not wired to protocol/dispatch scheduling |

### 4) State machine inventory (explicit + implicit)

- Explicit
  - Protocol mode transitions + queue/scheduler state: `OpenSpecV3Host`. 
  - Serial transport link/handshake/sync state: `SerialMcuTransport` (`_handshake_complete`, heartbeat, sync-required).
  - GUI/controller state machine referenced in threading docs (`QStateMachine`).
- Implicit
  - Pipeline decision state: `accept/reject/unknown` via `decision_outcome_for_object`.
  - Bench safety fault state: `NORMAL/SAFE/WATCHDOG` mapped from transport + budget faults.
  - Scheduler window state in logs: `scheduler_window_missed` derived from queue age/staleness.
- Missing explicit machine
  - Firmware runtime command parser/executor machine for HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE.
  - Firmware actuator dispatch + verification state model.

### 5) Hardware boundary definition

| Boundary | Current implementation | Contract status |
|---|---|---|
| Host CV -> host scheduler | Python dataclass/function contracts | Implemented |
| Host scheduler -> serial wire | Framed packet + CRC + ACK parsing | Implemented |
| Serial wire -> MCU protocol engine | Fully emulated in Python `OpenSpecV3Host` | Implemented (simulation) |
| MCU protocol engine -> MCU queue | C ring queue primitive | Partial (no parser/dispatcher integration) |
| MCU queue -> physical actuator | No concrete driver/task in firmware tree | Missing |
| Physical actuator -> host verification | No hardware feedback channel/sensor ingestion | Missing |

### 6) Known ambiguity list

- Queue-depth authority split: host sim has authority model; firmware runtime authority not implemented.
- Trigger verification semantics undefined for hardware path (ACK accepted vs physical actuation confirmed).
- Timebase ownership between host `perf_counter` and MCU tick not unified by contract.
- `detect_timeout_fallback` can synthesize reject command in bench path; live behavior parity uncertain.
- Runtime-config selected detection profile fallback behavior exists; no deterministic lockstep manifest for deployed provider/model versions on MCU side.

### 7) Technical debt register (ranked by risk)

| Rank | Debt item | Risk level | Risk to determinism/safety |
|---:|---|---|---|
| 1 | Firmware main loop lacks protocol command executor and scheduler/actuator task wiring | Critical | No deterministic hardware execution path |
| 2 | No actuator confirmation feedback loop (sensor/ack extension) | Critical | Cannot verify trigger execution deterministically |
| 3 | Firmware UART ISR is placeholder; no frame parser + CRC + command dispatch | High | Wire contract not enforced on MCU |
| 4 | Host/bench can report ACK-level success without physical trigger evidence | High | False-positive completion state |
| 5 | Host/MCU timebase not contractually aligned | High | Trigger timing drift and unverifiable windows |
| 6 | Bench send-budget fallback emits synthetic response object | Medium | Mixed real/synthetic transport outcomes |
| 7 | Multiple state references (`mode/scheduler_state`) across layers without single runtime source in hardware path | Medium | State divergence risk |
| 8 | Training package is metadata/baseline focused and not tied to deterministic deployment artifact gating | Low | Release-readiness gap, not immediate trigger determinism blocker |

## Phase 2 — Gap Analysis

| Gap | Risk | Blocking? | Fix Complexity | Notes |
|---|---|---|---|---|
| MCU protocol runtime not implemented (HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE) | Critical | Yes | High | Python host emulator exists; firmware path missing equivalent |
| MCU actuator dispatch task not implemented | Critical | Yes | High | Queue exists; no dequeue->GPIO/actuator execution path |
| No deterministic trigger verification signal from hardware | Critical | Yes | Medium-High | Needed for "trigger -> verify" closure |
| UART receive/parser in firmware is stub | High | Yes | High | CRC/framing not applied on MCU |
| Host-to-MCU timebase contract undefined for trigger timestamps | High | Yes | Medium | Required for deterministic schedule windows |
| Boundary contract parity checks stop at constants/schema; no runtime protocol conformance harness against firmware target | High | Yes | Medium | Existing readiness script validates static parity only |
| Bench/live safety behavior mismatch risk (`detect_timeout_fallback`, synthetic response path) | Medium | No (for initial hardware bring-up), Yes (for release) | Medium | Can hide determinism regressions |
| Queue/state authority not explicitly assigned for production path | Medium | No (if single source chosen early) | Medium | Must be formalized before release |
| Absence of hardware-in-loop deterministic regression suite | Medium | No (bring-up), Yes (release) | Medium | Needed for repeatable acceptance gate |

## Phase 3 — Roadmap Construction

### Phase 3.1
- Objective
  - Implement firmware protocol command executor with OpenSpec v3 parity and deterministic state ownership on MCU.
- Files touched
  - `firmware/mcu/src/main.c`
  - `firmware/mcu/src/isr.c`
  - `firmware/mcu/src/scheduler.c`
  - `firmware/mcu/include/*.h` (protocol parser/state headers)
  - `firmware/mcu/config/firmware_config.h`
- Interface changes
  - Add MCU command handlers for HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE.
  - Add deterministic ACK/NACK serialization with canonical fields.
- Deterministic guarantees added
  - Single MCU-owned source for `mode`, `queue_depth`, `scheduler_state`.
  - CRC/framing validated before command execution.
- Validation method
  - Reuse Python protocol vectors against firmware target (serial loopback/harness).
  - Deterministic replay of fixed frame corpus and fixed command sequence.
- Exit criteria
  - 100% pass for protocol command conformance vectors.
  - Stable queue-depth/state snapshots across repeated runs.

### Phase 3.2
- Objective
  - Implement deterministic MCU actuator dispatcher from queue with bounded jitter and safe-mode gating.
- Files touched
  - `firmware/mcu/src/main.c`
  - `firmware/mcu/src/scheduler.c`
  - new actuator driver/task files under `firmware/mcu/src/`
  - `firmware/mcu/include/` actuator interfaces
- Interface changes
  - Add scheduler dequeue-driven actuation API.
  - Add execution result codes for success/missed-window/safe-blocked.
- Deterministic guarantees added
  - FIFO dispatch ordering for equal-priority queue entries.
  - Explicit safe-state suppression of actuation.
- Validation method
  - Deterministic pulse-timing harness with fixed tick input.
  - Verify dispatch order and latency bounds.
- Exit criteria
  - No undefined scheduler state transitions during stress.
  - Measured dispatch jitter within configured bounds.

### Phase 3.3
- Objective
  - Close trigger verification loop (hardware feedback -> host-visible deterministic evidence).
- Files touched
  - `contracts/mcu_response_schema.json`
  - `src/coloursorter/serial_interface/serial_interface.py`
  - `src/coloursorter/bench/serial_transport.py`
  - firmware response encoder/telemetry source files
- Interface changes
  - Extend ACK/telemetry to include deterministic trigger execution evidence fields (e.g., trigger_id, executed_ts_tick, execution_status).
- Deterministic guarantees added
  - Every accepted schedule command has terminal status: executed / rejected-safe / missed-window.
  - No silent command loss.
- Validation method
  - Command-ack correlation checks with unique IDs and strict schema validation.
- Exit criteria
  - 1:1 mapping between host-issued commands and terminal execution records.

### Phase 3.4
- Objective
  - Unify timing contract (host detect/decision time to MCU execution timebase).
- Files touched
  - `contracts/sched_schema.json`
  - `src/coloursorter/bench/runner.py`
  - `src/coloursorter/runtime/live_runner.py`
  - firmware timing/state modules
  - `docs/artifacts/hardware_readiness/timing/*` generation scripts
- Interface changes
  - Add explicit timebase fields and conversion contract for scheduled trigger windows.
- Deterministic guarantees added
  - Reproducible trigger scheduling decisions independent of wall-clock jitter.
- Validation method
  - Fixed-seed replay with injected transport jitter and bounded expected execution windows.
- Exit criteria
  - Timing conformance report passes configured worst-case envelope.

### Phase 3.5
- Objective
  - Align bench/live safety behavior and remove synthetic transport ambiguity for release readiness.
- Files touched
  - `src/coloursorter/bench/runner.py`
  - `src/coloursorter/runtime/live_runner.py`
  - `src/coloursorter/config/runtime.py`
  - safety/config docs and tests
- Interface changes
  - Make fallback behavior explicit and mode-scoped; disallow synthetic ACK substitution in production-equivalent runs.
- Deterministic guarantees added
  - Identical safety state transitions for equivalent faults across bench and live modes.
- Validation method
  - Differential test suite bench vs live with identical event traces.
- Exit criteria
  - Zero divergence in state-transition traces for matched scenarios.

### Phase 3.6
- Objective
  - Introduce deterministic HIL acceptance gate for release.
- Files touched
  - `tests/` (new HIL-focused deterministic suites)
  - `tools/firmware_readiness_check.py`
  - CI workflow definitions
- Interface changes
  - Add mandatory deterministic conformance checks (protocol, timing, trigger verification).
- Deterministic guarantees added
  - Release blocked on deterministic see->decide->trigger->verify evidence.
- Validation method
  - Automated repeated-run variance checks and pass/fail thresholding.
- Exit criteria
  - Consecutive-run reproducibility threshold met (defined in gate config).

## Phase 4 — Risk Containment

| Roadmap phase | Failure mode | Detection method | Rollback strategy | Test harness required |
|---|---|---|---|---|
| 3.1 protocol executor | Parser accepts malformed frame or wrong NACK mapping | Protocol fuzz + canonical vector tests | Revert to last passing firmware parser tag; disable hardware mode in runtime config | Serial protocol conformance harness |
| 3.2 actuator dispatcher | Queue drains out of order or actuates in SAFE | Ordered trace assertions + SAFE-mode invariant tests | Disable dispatcher task; force SAFE and queue reset path | Deterministic tick-driven dispatcher simulator |
| 3.3 trigger verification | Missing terminal status for accepted commands | Command/terminal-status reconciliation checker | Fallback to ACK-only mode flagged non-release; block production profile | Correlation ID end-to-end verifier |
| 3.4 timing contract | Timebase conversion drift beyond envelope | Timing envelope regression with injected jitter | Revert timebase conversion changes; pin previous scheduling policy | Replay + jitter injection timing harness |
| 3.5 safety alignment | Bench/live divergent decisions under same fault input | Differential trace comparator | Disable changed fallback strategy via config flag; restore previous behavior | Bench/live parity scenario suite |
| 3.6 HIL gate | Flaky HIL tests create false release blocks | Repeated-run variance monitor + flake classifier | Temporarily mark gate informational while root-causing, keep deterministic blockers strict | Automated HIL deterministic regression suite |
