# High-Priority Baseline Bean-Sorting System Plan

## Document Purpose
This document is an implementation-ready plan for a **baseline bean-sorting system** that:
- uses the provided Python pipeline as the structural starting point,
- integrates CV defect detection with mechanical reject actuation,
- performs robust end-to-end logging,
- runs baseline test batches for initial performance data,
- calibrates actuator timing against measured latency,
- and preserves modularity for future upgrades (model, actuator, logging, metrics).

This plan is intentionally explicit so it can be handed to another engineering assistant (including ChatGPT) and executed with minimal ambiguity.

---

## 1) Target Outcomes (Definition of Done)

The system is considered baseline-complete when all conditions below are true:

1. **Ready-to-run pipeline exists** with clear entrypoint(s) for:
   - training preparation/augmentation,
   - model inference + reject decision,
   - actuator command issuing,
   - and logging + artifact generation.
2. **Actuation safety invariant is enforced**:
   - no mechanical reject command is sent unless a detection event exceeds configured reject criteria.
3. **Structured logs are complete** for each processed object/frame event:
   - UTC timestamp,
   - frame ID/object ID,
   - predicted class,
   - confidence,
   - reject/non-reject decision,
   - actuator command status + parameters,
   - latency signals,
   - snapshot path.
4. **Dataset augmentation is implemented** (rotation, brightness/contrast, blur) and applied before baseline training/evaluation.
5. **Baseline test batch runs execute successfully** and produce artifacts suitable for follow-up metric computation.
6. **Actuator timing calibration path exists** and uses measured pipeline latency.
7. **Logs are metric-ready** for future automated computation of:
   - false positives,
   - false negatives,
   - throughput,
   - reject accuracy.
8. **Modules are replaceable** without architectural rewrites:
   - detection provider,
   - actuator transport/controller,
   - logging backend.

---

## 2) Architecture Blueprint (Modular Contract-First Design)

Implement and/or preserve these boundaries:

1. **Detection Module**
   - Input: frame (BGR ndarray), frame metadata.
   - Output: `ObjectDetection[]` with class + confidence + stable IDs.
   - Replaceable providers: OpenCV heuristic baseline and future YOLO/other model.

2. **Decision + Scheduling Module**
   - Input: detections + lane geometry + calibration.
   - Output: per-object decision payload + optional scheduled actuator command.
   - Safety gating lives here (or immediately before transport send).

3. **Actuator Module**
   - Input: validated scheduled command.
   - Output: transport response (ACK/NACK, queue depth, latency, state).
   - Must not receive commands for non-reject events.

4. **Logging Module**
   - Input: unified event context from detection/decision/actuation.
   - Output: append-only machine-readable logs (CSV/JSONL) + snapshots.

5. **Calibration Module**
   - Input: measured stage latencies + conveyor speed and geometry.
   - Output: calibrated trigger timing/offset with safety bounds.

6. **Baseline Runner Module**
   - Executes test batches end to end.
   - Emits artifacts and run metadata for post-analysis.

---

## 3) Safety and Correctness Rules (Non-Negotiable)

1. **No command without reject event**
   - Actuator command generation requires:
     - detection exists,
     - class mapped to reject label,
     - confidence >= threshold,
     - lane/calibration valid.

2. **Deterministic command-to-object mapping**
   - Never rely on positional zipping of independent arrays when mixed accept/reject events can occur.
   - Commands must carry `object_id` linkage back to originating detection/decision.

3. **Validation at interfaces**
   - Frame shape/type validated before detection.
   - Detection output validated for ID uniqueness, class enum, confidence range.
   - Command parameters validated for lane bounds and trigger range.

4. **Fail safe behavior**
   - Calibration load failures or out-of-bound mapping must disable actuation for affected objects and log explicit reason.

5. **Observability first**
   - If command is skipped due to safety condition, log explicit skip reason.

---

## 4) Data and Logging Schema (for Current Ops + Future Metrics)

### 4.1 Event log row (minimum required fields)
Each event row (JSONL preferred + CSV projection) should include:

- `run_id`
- `test_batch_id`
- `event_timestamp_utc`
- `frame_id`
- `object_id`
- `prediction_label` (e.g., accept/reject)
- `confidence`
- `decision_label` (accept/reject)
- `decision_reason` (including safety skip reasons)
- `lane_index`
- `trigger_mm`
- `trigger_timestamp_s` (projected)
- `actuator_command_issued` (bool)
- `actuator_command_payload` (serialized or key fields)
- `transport_ack_code`
- `transport_nack_code`
- `transport_nack_detail`
- `queue_depth`
- `ingest_latency_ms`
- `decision_latency_ms`
- `schedule_latency_ms`
- `transport_latency_ms`
- `cycle_latency_ms`
- `frame_snapshot_path`
- `ground_truth_label` (optional now, reserved for future metric automation)

### 4.2 Artifact layout
Recommended per-run artifact directory:

- `artifacts/baseline/<timestamp>_<run_id>/summary.json`
- `artifacts/baseline/<timestamp>_<run_id>/events.jsonl`
- `artifacts/baseline/<timestamp>_<run_id>/telemetry.csv`
- `artifacts/baseline/<timestamp>_<run_id>/frames/*.png`
- `artifacts/baseline/<timestamp>_<run_id>/config_snapshot.json`

### 4.3 Why this enables future metrics automatically
- **False positives/negatives**: join `prediction_label` vs `ground_truth_label` when labels are available.
- **Throughput**: count events per wall-clock interval using timestamps.
- **Reject accuracy**: compare commanded rejects and true defective labels.
- **Latency regressions**: monitor stage latency distributions over runs.

---

## 5) Augmentation and Training Baseline (Pre-metrics Hardening)

### 5.1 Required augmentations
Apply to training dataset with controlled randomness:
1. rotation (e.g., ±15°),
2. brightness/contrast adjustment,
3. Gaussian blur.

### 5.2 Operational requirements
- keep original + augmented variants,
- use fixed seed option for reproducible experiments,
- record augmentation policy in `config_snapshot.json`.

### 5.3 Baseline training outcome
- produce train artifact metadata containing:
  - model identifier/version,
  - label space,
  - input dimensions,
  - score threshold used at inference.

---

## 6) Actuator Timing Calibration Plan

### 6.1 Problem
Detection and command scheduling incur latency; reject command must align with bean arrival at reject point.

### 6.2 Baseline calibration loop
1. Measure per-cycle latencies (`decision + schedule + transport` minimum).
2. Estimate effective command issuance delay.
3. Compute trigger offset using conveyor speed and delay.
4. Clamp offset to safe bounds.
5. Apply offset in scheduling path.
6. Persist calibration sample size and timestamp in run artifact.

### 6.3 Validation criteria
- command timestamps are monotonic and plausible,
- no negative trigger distance/time,
- reject events align with expected conveyor travel window under nominal test settings.

---

## 7) Baseline Test Batch Execution Plan

### 7.1 Inputs
- replay frames or live source,
- lane geometry and calibration configs,
- detection provider config,
- run metadata (`run_id`, `test_batch_id`).

### 7.2 Execution steps
1. Initialize frame source + detector + pipeline + transport + logger.
2. For each frame:
   - run detection,
   - run decision/scheduling,
   - issue actuator command only for validated reject events,
   - save snapshot(s),
   - append full structured event log.
3. Close resources and write summary/report artifacts.

### 7.3 Baseline output checks
- non-empty events file,
- snapshots generated,
- summary generated,
- command issuance count equals number of valid reject decisions,
- no command rows where decision is accept.

---

## 8) Implementation Work Packages (Suggested Sequence)

### WP1 — Safety mapping fix (highest priority)
- ensure each scheduled command is explicitly linked to `object_id`.
- remove any fragile positional pairing that can misalign command and decision.

### WP2 — Model provider integration
- add CV model-backed detection provider adapter.
- add provider-specific runtime config for threshold/model path/class mapping.

### WP3 — Full structured logging + frame snapshots
- introduce unified event logger.
- ensure confidence, command payload, and snapshots are captured.

### WP4 — Augmentation + baseline training script/module
- implement augmentation primitives and orchestration.
- save training metadata artifact.

### WP5 — Calibration integration
- compute and apply offset from measured latencies.
- store calibration details in artifacts.

### WP6 — Baseline batch runner + artifacts
- add run IDs and test batch IDs.
- emit metric-ready artifacts with config snapshots.

### WP7 — Tests and acceptance gates
- unit tests for validation/safety invariants.
- integration tests for mixed detections and command correctness.
- regression checks on artifact schema fields.

---

## 9) Test Strategy (Minimum Baseline Gate)

1. **Unit tests**
   - detection output validation,
   - command boundary checks,
   - logging schema presence and field typing,
   - augmentation deterministic behavior under seed.

2. **Integration tests**
   - mixed accept/reject detections in one frame,
   - calibration missing/invalid scenarios,
   - transport NACK behavior and logging.

3. **End-to-end baseline run**
   - execute on representative test batch,
   - confirm artifacts generated and internally consistent.

4. **Safety assertions**
   - zero actuation events for purely accept frames,
   - all actuation events traceable to reject decision with confidence threshold pass.

---

## 10) Operator Notes for Threshold Tuning and Retraining

1. Start with conservative reject threshold to minimize false reject actuation.
2. Use baseline logs to inspect confidence distribution before changing threshold.
3. Tune one variable at a time:
   - confidence threshold,
   - color/model class mapping,
   - calibration offset.
4. Retrain model when drift is observed (lighting, camera angle, bean mix).
5. Version every retrained model and persist config snapshot with each run.

---

## 11) Suggested CLI/Runbook Additions

Add flags (or equivalent config fields):
- `--run-id`
- `--test-batch-id`
- `--artifact-root`
- `--enable-snapshots`
- `--ground-truth-manifest` (optional)
- `--detector-provider`
- `--detector-threshold`
- `--calibration-mode` (fixed/adaptive)

Operational runbook should include:
- startup checks,
- emergency stop/safe mode behavior,
- artifact verification checklist,
- rollback steps for model/config changes.

---

## 12) Handoff Checklist for Next Engineer / ChatGPT

Before implementation begins, confirm:
- [ ] module boundaries and interfaces are accepted,
- [ ] safety invariants are understood,
- [ ] required schema fields are finalized,
- [ ] calibration assumptions (speed, geometry) are documented,
- [ ] baseline dataset source and labeling quality are known.

After implementation, confirm:
- [ ] end-to-end run succeeds,
- [ ] logs include all required fields,
- [ ] no unsafe actuation occurred,
- [ ] artifacts can drive automatic metric scripts,
- [ ] docs include threshold tuning + retraining instructions.

---

## 13) Minimal Pseudocode Reference (Implementation Skeleton)

```python
for frame in frame_source:
    ts = now_utc()
    detections = detector.detect(frame)

    for det in detections:
        decision = decision_engine.evaluate(det, frame_meta, calibration, geometry)

        command = None
        if decision.is_reject and decision.confidence >= threshold and decision.safety_ok:
            command = scheduler.build(decision)
            transport_resp = actuator.send(command)
        else:
            transport_resp = None

        snapshot_path = snapshot_writer.save(frame, frame_id=frame.id, object_id=det.object_id)

        logger.append_event(
            run_id=run_id,
            test_batch_id=batch_id,
            timestamp=ts,
            frame_id=frame.id,
            object_id=det.object_id,
            prediction=decision.prediction,
            confidence=decision.confidence,
            decision=decision.label,
            decision_reason=decision.reason,
            command=command,
            transport=transport_resp,
            latencies=current_latencies,
            snapshot_path=snapshot_path,
        )
```

This skeleton emphasizes the key baseline properties: **safe actuation gating**, **object-level traceability**, and **metric-ready logging**.
