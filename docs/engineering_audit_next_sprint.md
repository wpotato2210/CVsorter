# ColourSorter Engineering Audit (Repository State)

## 1) Completion Assessment

### 1.1 Module-by-module completeness

| Module / Area | Scope observed | Bench-mode completeness | Hardware-ready completeness | Evidence (files + symbols) | Completion estimate |
|---|---|---:|---:|---|---:|
| `preprocess` | Lane geometry load + lane index mapping implemented and validated. | 95% | 85% | `src/coloursorter/preprocess/lane_segmentation.py` (`load_lane_geometry`, `lane_for_x_px`), tests in `tests/test_preprocess.py`. | 90% |
| `calibration` | Calibration file loading + px→mm map + hash validation present. | 95% | 80% | `src/coloursorter/calibration/mapping.py` (`load_calibration`, `Calibration`), tests in `tests/test_integration.py`. | 88% |
| `eval` | Rule-based reject/accept decision path implemented. | 90% | 85% | `src/coloursorter/eval/rules.py` (`rejection_reason_for_object`), tests in `tests/test_eval_rules.py`. | 88% |
| `deploy` | End-to-end decision + schedule orchestration implemented; object detection provider is simplistic OpenCV contour path only. | 85% | 65% | `src/coloursorter/deploy/pipeline.py` (`PipelineRunner.run`), `src/coloursorter/deploy/detection.py` (`OpenCvDetectionProvider.detect`, abstract `DetectionProvider.detect`). | 75% |
| `scheduler` | Command model and range guards implemented. | 95% | 90% | `src/coloursorter/scheduler/output.py` (`build_scheduled_command`), tests `tests/test_scheduler.py`. | 92% |
| `serial_interface` | Framing/parser/ACK-NACK parsing implemented; schedule wire encoder in separate module. | 95% | 90% | `src/coloursorter/serial_interface/serial_interface.py`, `src/coloursorter/serial_interface/wire.py`, tests `tests/test_serial_interface.py`. | 92% |
| `protocol` host model | OpenSpec-v3 command handling, queue semantics, NACK code behavior implemented in software host model. | 95% | 70% | `src/coloursorter/protocol/host.py` (`OpenSpecV3Host.handle_frame`, `_set_mode`, `_sched`), tests `tests/test_protocol_compliance_v3.py`. | 82% |
| `bench` runtime | Bench runner, transport abstractions, mock + serial transport, encoder, evaluation artifacts implemented. | 95% | 75% | `src/coloursorter/bench/runner.py`, `mock_transport.py`, `serial_transport.py`, `virtual_encoder.py`, `evaluation.py`; tests across `tests/test_determinism_and_telemetry.py`, `tests/test_serial_transport.py`, `tests/test_bench_evaluation.py`. | 85% |
| GUI bench app | Replay/live flow, state transitions, SAFE/watchdog handling, queue and overlays implemented. | 90% | 65% | `gui/bench_app/controller.py`, `gui/bench_app/app.py`; tests `tests/test_bench_controller.py`, `tests/test_camera.py`. | 78% |
| Config/runtime loading | Runtime config validation, enum migration, transport/cycle/scenario thresholds implemented. | 95% | 80% | `src/coloursorter/config/runtime.py`, docs `docs/bench_runtime_config_migration.md`, tests `tests/test_runtime_config.py`. | 88% |
| Train artifacts | Artifact schema and metadata persistence present; training pipeline itself not present in repository runtime path. | 60% | 40% | `src/coloursorter/train/artifact.py`, tests `tests/test_train_artifact.py`. | 50% |
| Governance/OpenSpec docs | v3 artifact set is present (state machine, ICD, timing, telemetry, matrices, contracts, mirrored assets). | 95% | 90% | `docs/openspec/v3/*`, `docs/openspec/icd.md`, `openspec.md`, `tests/test_openspec_artifacts.py`. | 92% |

### 1.2 Bench-mode vs hardware-ready coverage

| Capability | Bench-mode state | Hardware-ready state | Audit status |
|---|---|---|---|
| End-to-end cycle (ingest→decision→schedule→transport logging) | Implemented in `BenchRunner.run_cycle`. | Serial path present but no MCU firmware/runtime module in repo to verify real target semantics. | Partial |
| Transport behavior | Deterministic mock queue model + serial retry/timeout logic implemented. | Serial integration depends on external MCU response behavior not versioned here. | Partial |
| SAFE/watchdog lifecycle | Bench controller + transport fault mapping implemented. | SAFE/AUTO semantics diverge between GUI operator flow and host model. | At risk |
| Queue depth/state observability | Available in mock transport and ACK metadata parser. | GUI queue depth returns 0 for serial transport path (`_transport_queue_depth`). | At risk |
| Camera/detection | Live/replay frame source paths exist. | Detection implementation remains baseline contour heuristic only. | Partial |

### 1.3 Completion percentage summary

| Roll-up | Estimated completion |
|---|---:|
| Bench-mode overall | 91% |
| Hardware-ready overall | 74% |
| Repository overall (combined) | 83% |

---

## 2) OpenSpec v3 Compliance

### 2.1 State machine coverage vs formal spec

| Spec requirement | Repository state | Evidence | Status |
|---|---|---|---|
| Modes AUTO/MANUAL/SAFE implemented | Implemented in host + GUI runtime state. | `docs/openspec/v3/state_machine.md`; `src/coloursorter/protocol/host.py`; `gui/bench_app/controller.py`. | Covered |
| Queue clear on mode change | Implemented in host `SET_MODE` handling. | `OpenSpecV3Host._set_mode`. | Covered |
| SAFE→AUTO direct transition invalid in host state machine | Implemented as NACK-5 in host. | `OpenSpecV3Host._set_mode`. | Covered |
| GUI operator recovery behavior | GUI allows SAFE→AUTO direct recovery path through `recover_to_auto` when in SAFE state. | `gui/bench_app/controller.py::recover_to_auto`; spec text also states direct GUI recovery is allowed. | Divergent policy surface |
| Scheduler states IDLE/ACTIVE | Emitted by host ACK parser/model; bench mock default states are simplified. | `parse_ack_tokens`; `OpenSpecV3Host._ack`; `TransportResponse`. | Partially covered |

### 2.2 Protocol command compliance (ACK/NACK, args, lane range)

| Protocol item | State | Evidence | Status |
|---|---|---|---|
| Commands `SET_MODE`,`SCHED`,`GET_STATE`,`RESET_QUEUE` | Implemented and tested. | `src/coloursorter/protocol/host.py::handle_frame`; `tests/test_protocol_compliance_v3.py::test_protocol_supports_all_v3_commands`. | Covered |
| NACK codes 1..8 and details | Implemented and parser-bounded to 1..8. | `host.py::_nack`; `serial_interface.py::parse_ack_tokens`; compliance tests. | Covered |
| Lane range 0..21 and trigger 0..2000 | Guarded in both scheduler and host. | `scheduler/output.py`; `protocol/host.py::_sched`; tests cross-check bounds. | Covered |
| ACK payload shape mode|queue|state|queue_cleared | Host emits and parser validates. | `host.py::_ack`; `serial_interface.py::parse_ack_tokens`. | Covered |
| NACK semantic mapping in bench fault model | `nack_code==7` mapped to watchdog, while protocol defines code 7 as BUSY. | `bench/serial_transport.py::_map_ack_to_bench_state`; `docs/openspec/v3/protocol/commands.json`. | Non-compliant mapping risk |

### 2.3 Telemetry schema coverage in logs

| Required OpenSpec field | Bench log model | CSV artifact export | Status |
|---|---|---|---|
| `frame_timestamp` | `BenchLogEntry.frame_timestamp_s` | Exported as `frame_timestamp`. | Covered |
| `trigger_timestamp` | `BenchLogEntry.trigger_timestamp_s` | Exported as `trigger_timestamp`. | Covered |
| `trigger_mm` | `BenchLogEntry.trigger_mm` | Exported as `trigger_mm`. | Covered |
| `lane_index` | `BenchLogEntry.lane_index` | Exported as `lane_index`. | Covered |
| `rejection_reason` | `BenchLogEntry.rejection_reason` | Exported. | Covered |
| `belt_speed_mm_s` | `BenchLogEntry.belt_speed_mm_s` | Exported. | Covered |
| `queue_depth` | `BenchLogEntry.queue_depth` | Exported. | Covered |
| `scheduler_state` | `BenchLogEntry.scheduler_state` | Exported. | Covered |
| `mode` | `BenchLogEntry.mode` | Exported. | Covered |

### 2.4 Timing-budget alignment (ingest→decision→schedule→transport)

| Budget / timing requirement | Repository state | Status |
|---|---|---|
| Stage timings emitted | All five stage timing fields and cycle latency are emitted per log entry. | Covered |
| Nominal RTT target validation | Scenario thresholds and integration tests validate average/peak RTT behavior in bench. | Covered (bench) |
| Retry/backoff policy (100ms timeout, 3 retries) | Implemented in serial transport config defaults and retry loop behavior. | Covered |
| Hard runtime enforcement against budget breach | No in-cycle enforcement gate; budgets are evaluated post-hoc via scenario evaluation/tests. | Partial |

---

## 3) Test Coverage

### 3.1 Automated test presence per module

| Module / concern | Automated tests present | Coverage status |
|---|---|---|
| Preprocess/lane geometry | `tests/test_preprocess.py` | Present |
| Calibration/mapping + integration | `tests/test_integration.py` | Present |
| Eval rules | `tests/test_eval_rules.py` | Present |
| Scheduler range guards | `tests/test_scheduler.py` | Present |
| Serial framing + ACK/NACK parse | `tests/test_serial_interface.py` | Present |
| OpenSpec protocol semantics | `tests/test_protocol_compliance_v3.py` | Present |
| Serial retry/fault parsing | `tests/test_serial_transport.py` | Present |
| Determinism + telemetry | `tests/test_determinism_and_telemetry.py` | Present |
| GUI controller behavior | `tests/test_bench_controller.py`, `tests/test_camera.py` | Present |
| OpenSpec artifact parity | `tests/test_openspec_artifacts.py` | Present |

### 3.2 Untested or weakly tested paths (requested critical paths)

- **Mode transitions**
  - Host SAFE→AUTO rejection and mode transitions are tested.
  - GUI SAFE→AUTO direct recovery flow exists and is tested for controller behavior, but cross-interface consistency (GUI action vs host protocol transition constraints) is not validated end-to-end.
- **Queue clearing**
  - Host queue clear on mode change/RESET_QUEUE is tested.
  - Serial transport queue visibility/clearing in GUI is weak: GUI queue depth and clear helpers are mock-only (`_transport_queue_depth`, `_transport_clear_queue`) with no serial equivalent behavior verification.
- **Encoder fault handling**
  - Deterministic zero-speed/missing-pulse/dropout quantization are tested at encoder and runner levels.
  - Fault-injection beyond current toggles (e.g., bursty pulse jitter, timestamp skew) is not represented.
- **SAFE entry/exit**
  - SAFE entry and recovery flows are covered in protocol and controller tests.
  - SAFE exit under real serial/host command exchange is not tested in repo (bench controller transitions are local state operations).

### 3.3 GUI vs headless coverage

| Dimension | Current state |
|---|---|
| Headless/core coverage | Strong: protocol, parser, transport, runner, evaluation, config modules all have direct tests. |
| GUI coverage | Moderate: controller state transitions and label updates are tested using offscreen Qt, but not full replay/live serial-device integration. |
| End-to-end hardware path | Limited in repository-only execution (depends on external serial endpoint). |

---

## 4) Interface & Protocol Risks

- **Host ↔ MCU mismatch risk**
  - Bench serial transport maps `NACK` code 7 to watchdog semantics, while OpenSpec assigns code 7 to BUSY.
  - Operational interpretation of BUSY vs WATCHDOG can diverge in dashboards and SAFE escalation.
- **Lane index and scheduling constraints risk**
  - Lane/trigger constraints are consistent in host and scheduler, but queue depth behavior differs between mock and serial monitoring in GUI.
- **ACK/NACK semantic inconsistencies**
  - Host emits rich ACK metadata; mock transport ACK path mostly returns defaults (`mode="AUTO"`, `scheduler_state="IDLE"`, `queue_cleared=False`) without state-machine fidelity.
- **Telemetry token consumption gaps**
  - Telemetry schema fields are present, but serial GUI queue depth token consumption is absent (depth always 0 for non-mock transport).
  - `trigger_timestamp_s` is derived from pulse presence, not from a physically projected trigger execution moment at transport/scheduler boundary.

---

## 5) Determinism & Fault Risks

- **Encoder pulse handling (quantization / accumulator)**
  - Accumulator logic is deterministic and tested for low-speed and dropout quantization.
  - Dropout is deterministic ratio-based truncation; stochastic/noise-model behavior is not represented.
- **Queue consumption vs transport timing**
  - Queue consumption policies (`none`, `one_per_tick`, `all`) are implemented only for mock transport cycle stepping.
  - Serial mode lacks equivalent explicit queue consumption model in GUI runtime.
- **Trigger timestamp correctness**
  - `trigger_generation_s`/`trigger_timestamp_s` are pegged to current or previous frame time depending on pulse count, not modeled against trigger distance + belt kinematics.
- **Latency/jitter risk**
  - Stage timings are measured and logged, but response to budget overrun is post-run evaluation rather than runtime control gating.

---

## 6) Technical Debt

- **Code duplication / split protocol helpers**
  - Protocol constants and boundaries are represented across scheduler, host, protocol JSON artifacts, and parser logic; synchronization relies on tests rather than single shared source.
- **Mixed wire representations**
  - Wire frame handling lives in `serial_interface.py`, with command-specific encoding in `wire.py`, plus host protocol handling in `protocol/host.py` (multiple representations of same contract).
- **Runtime SAFE logic split across modules**
  - SAFE handling spans host state machine, serial transport fault mapping, mock transport behavior, and GUI controller recovery methods.
- **Additional maintainability risks**
  - Detection abstraction includes base class with `NotImplementedError`; production detector behavior remains baseline heuristic.
  - GUI controller contains combined concerns (state machine, transport orchestration, UI wiring, recovery logging) in one large class.

---

## 7) Governance Artifact Gaps

### 7.1 Presence check for requested OpenSpec artifacts

| Artifact | Presence | State assessment |
|---|---|---|
| State machine | Present (`docs/openspec/v3/state_machine.md`) | Present; includes both host and operator recovery language that can create dual-policy interpretation. |
| ICD | Present (`docs/openspec/icd.md`) | Present; interface definitions captured. |
| Timing budget | Present (`docs/openspec/v3/timing_budget.md`) | Present; mostly bench-centric targets. |
| Telemetry schema | Present (`docs/openspec/v3/telemetry_schema.md`) | Present; required fields align with telemetry writer. |
| Compliance matrices | Present (`docs/openspec/v3/system_compliance_matrix.md`, `docs/openspec/v3/protocol_compliance_matrix.md`) | Present; traceability largely test-reference based and bench-focused. |

### 7.2 Gap notes (artifact quality/completeness)

- Artifact set is complete by filename, but hardware/runtime acceptance criteria remain predominantly bench-defined.
- Compliance references are strong for unit/integration tests, with limited explicit external-MCU interoperability evidence inside the repository.

---

## 8) Execution-Ready Recommendations (Summary Table Only — Classification)

| Gap / risk classification | Module / area | Priority | Effort (S/M/L) | Include next sprint (Yes/No) |
|---|---|---|---|---|
| NACK code-7 semantic mismatch (BUSY vs WATCHDOG interpretation) | `src/coloursorter/bench/serial_transport.py` + protocol layer | High | S | Yes |
| SAFE policy split between host transition rules and GUI recovery flow | `src/coloursorter/protocol/host.py`, `gui/bench_app/controller.py`, `docs/openspec/v3/state_machine.md` | High | M | Yes |
| Serial-mode queue depth/clear observability gap in GUI | `gui/bench_app/controller.py` | High | M | Yes |
| Trigger timestamp tied to pulse presence rather than transport-aligned trigger model | `src/coloursorter/bench/runner.py`, `virtual_encoder.py` | High | M | Yes |
| Bench/hardware parity not fully evidenced in-repo | Transport + integration boundary | High | L | Yes |
| Protocol constants duplicated across code/artifacts | scheduler/protocol/serial modules + docs artifacts | Medium | M | Yes |
| Mixed wire representation layers increase drift risk | `serial_interface.py`, `wire.py`, `protocol/host.py` | Medium | M | Yes |
| Controller class concentration of concerns | `gui/bench_app/controller.py` | Medium | M | No |
| Detection provider maturity baseline only | `src/coloursorter/deploy/detection.py` | Medium | L | Yes |
| Post-hoc timing-budget evaluation only | `bench/runner.py`, `bench/evaluation.py`, scenarios | Medium | M | Yes |
| Stochastic encoder/fault profiles absent (only deterministic toggles) | `virtual_encoder.py`, determinism tests | Low | M | No |
| Governance artifacts bench-centric for compliance evidence | `docs/openspec/v3/*` | Low | M | No |



---

## 9) Provided Sprint Plan Consistency Check (State-Only)

| Task ID | Declared phase | Referenced files/paths in task | Repo path validity | Command/checkpoint validity vs repo state | Audit classification |
|---|---|---|---|---|---|
| `phase1-01` | Bench Stabilization | `tests/` | Valid | `pytest -q --tb=short tests/` is valid. `bench_log.csv`, `telemetry_artifacts/`, and their baseline targets are not repository-root artifacts produced by default test run. | Command partially mismatched to repo artifact layout |
| `phase1-02` | Bench Stabilization | `bench/runner.py`, `bench/evaluation.py` | Path mismatch (runtime files are under `src/coloursorter/bench/`) | Requested stage timing fields are already present in `BenchLogEntry` and exported in CSV (`ingest_latency_ms`, `decision_latency_ms`, `schedule_latency_ms`, `transport_latency_ms`, `cycle_latency_ms`). | Already implemented; task target paths stale |
| `phase2-03` | High-Risk Module Isolation | `protocol/host.py`, `serial_interface.py`, `scheduler/output.py`, `docs/openspec/v3/protocol_commands.json` | Path mismatch for all code/doc targets (`src/coloursorter/...` and `docs/openspec/v3/protocol/commands.json`) | Task intent aligns with identified duplication risk; command references a test file that exists (`tests/test_protocol_compliance_v3.py`). | Valid risk theme, invalid path assumptions |
| `phase2-04` | High-Risk Module Isolation | `protocol/host.py`, `gui/bench_app/controller.py` | Mixed validity (`gui/...` valid, `protocol/...` path stale) | Task intent aligns with identified SAFE-policy split. Provided command text in instruction payload is truncated (`tests/test_benc...`) and not executable as-is. | High-priority risk, execution command incomplete |

### Sprint-plan ingestion risks observed from provided payload

- The JSON task payload appears truncated in this handoff (final command for `phase2-04` is incomplete), so the plan cannot be treated as fully machine-executable in current form.
- Several task file paths use pre-package-root assumptions (missing `src/coloursorter/` prefix), creating path-resolution ambiguity for implementation tracking.
- At least one task describes functionality already present in repository state (per-stage timing fields), indicating baseline drift between sprint plan and current codebase snapshot.
