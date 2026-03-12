# Complete Engineering Report — CVsorter

Date: 2026-03-12  
Reviewer role: Senior software engineer + CV researcher + systems architect

---

## 1) Project Overview

### What the system does
CVsorter is a deterministic vision-to-actuation stack for lane-based sorting. The host side ingests frames (replay/live), runs detection, maps detections to lane geometry + calibration, applies reject logic, schedules commands, and sends commands to a transport that emulates or talks to MCU hardware.

### High-level architecture
1. **Ingest / source**: replay/live frame sources and ingest boundary.
2. **Detection**: OpenCV basic/calibrated or model stub provider.
3. **Preprocess + geometry/calibration**: lane geometry loading/alignment and px→mm conversion.
4. **Decisioning**: rule-based reject policy producing deterministic decision payloads.
5. **Scheduling**: lane + trigger mm converted to scheduled command with contract bounds.
6. **Transport/protocol**: wire framing (`<MSG|CMD|payload|CRC>`), ACK/NACK parsing, mock/serial/ESP32 transport adapters.
7. **Bench + GUI**: benchmark runner, scenario evaluation, telemetry/artifact generation, PySide6 bench control plane.
8. **Firmware module set**: scheduler/queue/watchdog/safety ISR-oriented C modules.

### Data flow (host)
`frame -> detection -> (lane mapping + calibration + eval rules) -> decision payload -> scheduled command -> transport -> ACK/NACK + telemetry`.

### External dependencies
- CV/ML stack: OpenCV, NumPy, Torch, Ultralytics.
- GUI: PySide6.
- Optional transport: pyserial.

---

## 2) Code Quality

### Strengths
- Good use of `dataclass(frozen=True)` for contract-like models and immutable payloads.
- Strong runtime boundary checks in many core paths (frame shape/type, command bounds, config ranges).
- Naming is mostly consistent and domain-driven (`PipelineRunner`, `RuntimeConfig`, `OpenSpecV3Host`, `BenchSafetyConfig`).
- Tests are extensive in count and include protocol/timing/GUI checks.

### Weaknesses / smells
1. **Monolithic methods**
   - `BenchRunner.run_cycle` is very long and mixes timing, fault arbitration, scheduling, transport, telemetry materialization, and policy fallback logic in one method. This hurts readability and test isolation.

2. **Duplication in threshold/profile resolution**
   - `_resolve_runtime_reject_thresholds` logic appears in multiple modules (bench CLI, GUI controller, live runtime), creating drift risk.

3. **Tight coupling via package-level imports**
   - `RuntimeConfig` validation reaches into deploy detection provider resolution (`_validate_detection_provider_name`), coupling config parsing to deploy package import behavior.

4. **Custom YAML parser complexity**
   - A hand-rolled YAML subset parser increases parser maintenance burden and edge-case risk versus a constrained safe loader + schema validation.

5. **Type contract gaps**
   - Some APIs use `object` for frames and manual runtime checks; this is defensible for boundary hardening but weak for static typing and IDE discoverability.

---

## 3) Architecture Analysis

### Separation of concerns
- Core module boundaries are mostly sensible: preprocess, calibration, eval, scheduler, protocol, transport, runtime, GUI, firmware.
- However, orchestration layers (bench runner + GUI controller) aggregate too many concerns and become “god objects”.

### Dependency structure
- Direction is mostly top-down, but there is notable cross-layer coupling:
  - config validation calling deploy provider resolver;
  - runtime/bench modules embedding transport-specific policy branches;
  - GUI controller owning domain policy, queueing, threading, state transitions, transport setup, and mode recovery.

### Testability/extensibility
- Testability is good for module-level contracts.
- Extensibility is moderate: adding a detector provider is straightforward; adding a new safety gate requires touching multiple orchestration paths.

### Architectural risks
- **Hidden side effects**: pipeline runner reloads files based on mtime during `run`, so each cycle can mutate runner internals.
- **Time-dependent paths**: real-time code paths rely on `time.perf_counter` / `time.monotonic` directly in hot loops.
- **Potential drift between bench and live orchestration**: duplicated logic around profile resolution/fallback and safety handling.

### Suggested architecture improvements
- Split `BenchRunner.run_cycle` into deterministic pure stages (`ingest_guard`, `decision_stage`, `schedule_stage`, `transport_stage`, `log_stage`).
- Extract shared “runtime profile resolution + reject threshold resolution” service used by CLI/GUI/live runner.
- Isolate config parser from deploy package by moving provider-name validation to config-owned constants or an injected validator.

---

## 4) Computer Vision Pipeline

### Current pipeline characteristics
- **Input contract**: BGR uint8 `(H,W,3)` for detection providers.
- **Preprocessing**: exposure normalization + gray-world white balance (`_normalize_frame`) with clipping metrics.
- **Feature/segmentation**: grayscale threshold + contour extraction (OpenCV) for object proposals.
- **Geometry extraction**: centroid from image moments; lane assignment from lane boundaries.
- **Filtering/rules**: reject based on infection/curve/size thresholds and classifier label.
- **Output**: deterministic list of `ObjectDetection`, then `DecisionPayload`, then scheduled command.

### Evaluation
- **Algorithm choice**: OpenCV threshold + contours is fast/deterministic and suitable for controlled bench conditions.
- **Numerical stability**: basic safeguards exist (moment zero checks, confidence clipping, finite checks in config/protocol), but contour thresholding is sensitive to lighting shift.
- **Robustness to noise**: calibrated HSV path and normalization help, but no temporal filtering/tracking across frames.
- **Real-time suitability**: good for CPU in moderate frame sizes; deterministic ordering enforced by sorting detections by ID in OpenCV paths.

### Failure cases
- Strong illumination gradients/specular highlights can break fixed threshold segmentation.
- Lane alignment degradation only marks fault reason; no adaptive geometry correction beyond scale + offset.
- No explicit per-frame uncertainty propagation from detection to scheduler beyond binary reject decisions.

### CV improvements
- Add deterministic temporal association (e.g., nearest-neighbor tracker with fixed gating) to stabilize per-object decisions.
- Replace fixed global threshold with deterministic adaptive thresholding or color constancy-aware segmentation profile.
- Add morphology post-processing (opening/closing) with fixed kernels to reduce noise contours.

---

## 5) Performance Analysis

### Complexity and hotspots
- Detection providers are contour-based and mostly linear in pixels + contour count.
- Bench/logging path allocates many objects per detection per cycle; this is likely a major Python-side overhead in high-FPS conditions.
- Repeated per-cycle checks and dynamic object creation (`type("_Resp", ...)`) in bench runner increase overhead and reduce clarity.

### CPU/GPU utilization
- CV path currently CPU-dominant in OpenCV providers.
- Training/inference path supports configurable device placement but bench runtime path is predominantly CPU.

### Optimization opportunities
- Pre-allocate/reuse temporary structures in runner loop.
- Decompose log-entry build path to avoid repeated conversions.
- Consider NumPy vectorized preprocessing for batched frames if multi-frame buffering is introduced deterministically.

---

## 6) Reliability and Error Handling

### Good practices
- Protocol framing and CRC checks are strict.
- ACK/NACK parsing validates token counts/ranges.
- Config validation is comprehensive with explicit range checks.

### Reliability risks
1. **Environment fragility in readiness check**
   - Firmware readiness script can fail runtime config check due to `libGL.so.1` import chain issues in headless environments.
2. **Broad exception handling in startup paths**
   - Some broad `except Exception` blocks return generic failure details; useful operationally but can hide root causes unless logs are preserved.
3. **State mutation in-run**
   - Hot-path configuration reload by mtime can produce mid-run behavior changes if files are touched.

### Potential crash points
- Camera and serial transport initialization boundaries.
- GUI threading and queue-drain interactions if timers/workers race unexpectedly.

---

## 7) Testing Quality

### Current test posture
- Large suite (~348 test functions) covering pipeline, protocol, transport, bench, GUI, determinism contracts.
- Dedicated tests for protocol versioning, transport jitter/fault gates, scheduler acceptance, GUI state/mode transitions.

### Gaps
- Limited explicit performance regression tests (latency envelope under realistic sustained load).
- Limited fuzz/robustness tests for malformed frame payloads beyond deterministic fixture cases.
- Firmware readiness strict test currently sensitive to host graphics/OpenCV runtime environment.

### Recommended test strategy additions
- Deterministic soak tests for long-run queue/latency drift.
- Property-based tests for frame parser and ACK/NACK token parsing.
- Bench-vs-live parity golden traces for same replay data.

---

## 8) Dependency and Environment Management

### Strengths
- `pyproject.toml` as source of truth with guarded version ranges.
- `requirements.txt` generated from project metadata.
- Optional extras for serial/test/lint are defined.

### Risks
- Version ranges are broad enough to permit drift (especially heavy CV/ML stack).
- OpenCV runtime environment differences (headless vs system libs) can break checks/tests.
- PySide6 in core dependencies increases install surface even for non-GUI use.

### Recommendations
- Add lockfile strategy for CI reproducibility (pip-tools/uv/poetry lock equivalent).
- Split minimal runtime profile from full GUI+ML profile if possible.
- Add environment matrix tests for headless Linux vs desktop environments.

---

## 9) Security and Safety

### Security posture
- No obvious unsafe deserialization primitives beyond controlled JSON loading and a constrained custom YAML parser.
- Protocol parser validates framing, CRC, and tokens.
- File operations are mostly explicit and local-path based.

### Risks
- Custom parser maintenance risk can become security risk if parser complexity grows.
- Ground-truth/snapshot path handling should remain constrained to project artifact roots to avoid accidental path traversal in future changes.

### Safety posture
- Protocol and scheduler guardrails are explicit.
- Mode transition policy and SAFE handling are present.
- Hardware-facing loops still require stronger end-to-end watchdog proof under fault injection in real hardware.

---

## 10) Field Deployment Readiness

### Lab testing
**Status: Ready with caveats.** Bench + mock transport + replay are strong.

### Vehicle/integrated conveyor testing
**Status: Partially ready.** Protocol and scheduler semantics are mature, but hardware integration confidence depends on serial/ESP32 behavior under sustained load and jitter.

### Autonomous operation
**Status: Not yet fully ready.** Need stronger fault containment proof, long-duration stability metrics, and stricter environment hardening.

### Safety-critical use
**Status: Not ready.** Current evidence is strong for deterministic engineering discipline but insufficient for safety certification-grade assurance.

---

## 11) Technical Debt (Prioritized)

### P0 (high)
1. Bench runner orchestration complexity (`run_cycle`) and mixed responsibilities.
2. Runtime-config/deploy coupling causing environment-sensitive import failures.
3. Firmware/host lane-capacity mismatch risk (host lane range 0..21 vs firmware default lane max 8 unless configured).

### P1 (medium)
4. Duplication of threshold/profile resolution logic across modules.
5. Custom YAML parser maintenance burden.
6. Repeated dynamic response-object construction in hot path.

### P2 (lower)
7. Incomplete performance benchmarking under prolonged load.
8. Broad dependency footprint for simple bench-only flows.

---

## 12) Recommended Improvements

### Short-term (1–2 sprints)
- Refactor `BenchRunner.run_cycle` into pure stage functions with explicit I/O dataclasses.
- Isolate config validation from deploy package imports to remove OpenCV-linked startup fragility.
- Add deterministic integration test for host lane max vs firmware lane max contract parity.
- Consolidate shared reject-threshold/profile resolution logic in one module.

### Medium-term (1–2 quarters)
- Introduce a small “runtime orchestration kernel” shared by CLI, live runtime, and GUI.
- Add deterministic temporal tracking module (fixed association rules, bounded state).
- Add reproducible performance benchmark suite with regression thresholds.

### Long-term
- Build a formal contract-verification layer that validates host/firmware/protocol consistency from generated contract artifacts.
- Move from ad-hoc benches to hardware-in-the-loop campaign automation with reproducible trace baselines.

---

## 13) Final Engineering Assessment

### Overall maturity
- **Research use:** strong.
- **Internal validation/testing:** strong-to-moderate.
- **Production deployment:** moderate, pending orchestration hardening + environment reproducibility + deeper hardware proof.
- **Safety-critical deployment:** low without formal assurance program.

### Strongest components
- Protocol framing/validation discipline.
- Deterministic data models and boundary checks.
- Extensive contract-oriented test suite.

### Weakest components
- Large orchestration methods with mixed responsibilities.
- Environment-sensitive dependency interactions.
- Potential host/firmware configuration drift points.

### Recommended next phase
“**Phase: Integration Hardening**” focused on:
1) orchestration decomposition,  
2) host/firmware parity automation,  
3) deterministic long-run performance & fault-injection evidence.

### Readiness scores (1–10)
- **Research use:** 8/10
- **Internal testing:** 7/10
- **Production use:** 5/10
- **Safety-critical deployment:** 2/10

