# Phase 2 System Integration Audit (Pipeline Correctness & Module Integration)

## 1) Pipeline architecture diagram (text)

```
Frame Source (ReplayFrameSource | LiveFrameSource)
  -> Detector (OpenCvDetectionProvider | CalibratedOpenCvDetectionProvider | ModelStubDetectionProvider)
      -> preprocess metrics (optional side-channel)
  -> PipelineRunner
      -> lane_geometry_for_frame + lane_for_x_px
      -> calibration px_to_mm
      -> decision_outcome_for_object (thresholds + fault context)
      -> build_scheduled_command
  -> Transport (MockMcuTransport | SerialMcuTransport | Esp32McuTransport)
      -> MCU ACK/NACK + queue telemetry
  -> BenchLogEntry / runtime reports
```

## 2) Data flow between major modules

- `bench/cli.py` selects source + detector + runner, captures frames, runs detection, and enqueues a normalized payload into ingest boundary (`runner.process_ingest_payload`).
- `ingest/adapter.py` validates payload and produces `IngestCycleInput` containing `FrameMetadata`, `ObjectDetection` objects, timing metadata, and preprocessing metrics.
- `bench/runner.py` calls `PipelineRunner.run(...)`, maps decisions to commands, applies timing budgets, and calls transport `send(...)` for scheduled commands.
- `deploy/pipeline.py` combines lane geometry, calibration, rule evaluation, and scheduler command generation into `PipelineResult`.
- In live mode, `runtime/live_runner.py` bypasses ingest boundary and directly executes: frame -> detector -> pipeline -> transport.

---

## Findings

### Issue 1
**SEVERITY:** HIGH  
**FILE:** `src/coloursorter/bench/runner.py`  
**LINES:** 136  
**PROBLEM:** Bench path does not pass reject thresholds or capture fault context into `PipelineRunner.run`, unlike live runtime.

**EVIDENCE (code snippet):**
```python
pipeline_result = self._pipeline.run(frame=frame, detections=detections)
```

**FAILURE SCENARIO:**
Bench qualification passes/fails on default profile behavior while live runtime uses configured thresholds and capture-fault gating. Phase 2 validation can approve a setup that behaves differently in production.

**RECOMMENDED FIX:**
Thread configured thresholds and capture fault reason into bench path exactly as live path does, so bench/live decision behavior is contract-equivalent.

### Issue 2
**SEVERITY:** HIGH  
**FILE:** `src/coloursorter/runtime/live_runner.py`  
**LINES:** 213, 342-374  
**PROBLEM:** Startup diagnostics are computed but not enforced as a run gate.

**EVIDENCE (code snippet):**
```python
self.startup_diagnostics = self._run_startup_diagnostics()
...
while max_cycles is None or cycle_count < max_cycles:
    frame = self._frame_source.next_frame()
    detections = self._detector.detect(frame.image_bgr)
```

**FAILURE SCENARIO:**
System logs startup failures (e.g., profile mismatch/transport ping failure) but still enters runtime loop, causing silent degraded operation during integration and masking preflight failures.

**RECOMMENDED FIX:**
Fail-fast when `startup_diagnostics.all_passed` is false (exception or explicit safe-mode lockout), with structured error output.

### Issue 3
**SEVERITY:** MEDIUM  
**FILE:** `src/coloursorter/bench/live_source.py`  
**LINES:** 39-42  
**PROBLEM:** Live source timestamps are synthetic (`frame_id * frame_period_s`) instead of actual capture time.

**EVIDENCE (code snippet):**
```python
timestamp_s=self._frame_id * self._config.frame_period_s,
```

**FAILURE SCENARIO:**
If real camera cadence deviates from configured period, trigger timing diagnostics drift from reality. Phase 2 timing acceptance may look stable while physical actuation alignment is off.

**RECOMMENDED FIX:**
Use monotonic capture timestamps at frame acquisition time; keep deterministic replay behavior only for replay source.

### Issue 4
**SEVERITY:** MEDIUM  
**FILE:** `src/coloursorter/ingest/adapter.py`  
**LINES:** 107-111  
**PROBLEM:** Ingest contract accepts channel counts `{1,3,4}` even though detection/pipeline integration assumes 3-channel BGR.

**EVIDENCE (code snippet):**
```python
if channels not in {1, 3, 4}:
    raise IngestValidationError("image_shape channels must be one of: 1, 3, 4")
```

**FAILURE SCENARIO:**
External ingest producer sends grayscale/RGBA payloads that pass boundary validation, but downstream detector interfaces expect BGR `(H,W,3)`; runtime then fails later and non-locally.

**RECOMMENDED FIX:**
Constrain ingest contract to 3 channels for this pipeline or introduce explicit, deterministic conversion before detection.

### Issue 5
**SEVERITY:** MEDIUM  
**FILE:** `src/coloursorter/runtime/live_runner.py`  
**LINES:** 202, 211  
**PROBLEM:** Hidden implicit dependency via monkey-patched attributes (`runtime_reject_thresholds`) on pipeline and detector.

**EVIDENCE (code snippet):**
```python
setattr(self._pipeline, "runtime_reject_thresholds", dict(self.runtime_reject_thresholds))
setattr(self._detector, "runtime_reject_thresholds", dict(self.runtime_reject_thresholds))
```

**FAILURE SCENARIO:**
Other modules/tests may rely on these dynamic attributes without interface contracts, creating fragile behavior across providers and making integration regressions hard to detect.

**RECOMMENDED FIX:**
Replace dynamic attributes with typed constructor parameters or explicit method arguments; document the contract in module interfaces.

### Issue 6
**SEVERITY:** MEDIUM  
**FILE:** `src/coloursorter/deploy/detection.py`  
**LINES:** 357-370  
**PROBLEM:** `ModelStubDetectionProvider` default predictor emits a fabricated center detection every frame.

**EVIDENCE (code snippet):**
```python
return [{"object_id": "det-0", ... "label": "accept", "confidence": 0.51}]
```

**FAILURE SCENARIO:**
If Phase 2 environment accidentally selects `model_stub`, pipeline appears functional and deterministic but is detached from real CV behavior, invalidating integration conclusions.

**RECOMMENDED FIX:**
Require explicit predictor injection in non-test environments, or hard-fail without predictor when running live/bench integration modes.

---

## 3) Integration risks

- Bench/live behavior divergence (threshold/fault-context mismatch).
- Preflight checks not enforcing runtime safety gate.
- Timebase inaccuracies in live capture affecting reject timing confidence.
- Boundary contract broader than downstream interface guarantees.
- Hidden dynamic state enabling silent coupling.
- Stub provider accidentally used as if real detector.

## 4) Most likely real-world failure during Phase 2

**Most likely:** a bench-qualified configuration fails in live integration because live runtime applies profile thresholds and capture-fault gating differently than bench flow, resulting in unexpected reject/accept behavior and timing discrepancies at the actuator.

## 5) Overall system maturity assessment

**Assessment:** **Moderate, integration-incomplete.**

- Core module decomposition is present and mostly deterministic.
- Critical integration paths still diverge between bench and live.
- Error/preflight handling is informative but not yet safety-enforcing.
- Interface contracts are partially explicit, but some are still implicit/monkey-patched.

System is close to usable for controlled testing, but Phase 2 sign-off should be blocked until bench/live parity and startup gating are enforced.
