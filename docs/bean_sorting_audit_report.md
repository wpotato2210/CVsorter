# Technical Audit Report — Bean Sorting Vision + Actuation System

## 1) Project Overview

### Purpose
- The project implements automated bean inspection and reject triggering, with software paths for detection, decisioning, and command scheduling toward an MCU-controlled reject mechanism.
- The current codebase is bench-first and appears designed to validate deterministic timing, protocol behavior, and safe-state transitions before full production coupling.

### Scope
- In-scope runtime modules include lane segmentation, calibration mapping, decision/rules evaluation, scheduling, and serial command framing.
- Bench simulation and GUI tooling are mature relative to production hardware ownership and are used to validate timing and protocol behavior in pre-production scenarios.
- Production deployment details (platform matrix, ownership model, release promotion policy) remain partially unspecified and are noted as open gaps.

### System Architecture (as implemented)
- **Vision/data path:** frame + detections → lane segmentation + calibration mapping → decision payload + reject reason.
- **Control path:** reject decision → scheduled command (`lane`, `position_mm`) → framed serial packet to MCU.
- **Operator/validation path:** bench runner + telemetry + GUI, with SAFE/MANUAL/AUTO mode controls and readiness evidence artifacts.

---

## 2) Technical Correctness

### CV model selection and justification
**Observed implementation**
- Detection provider options are classical OpenCV pipelines (`opencv_basic`, `opencv_calibrated`) based on thresholding + contour extraction + ROI color statistics (BGR/HSV), not deep learning.
- This is technically valid for controlled lighting and constrained part appearance, with low compute overhead and deterministic behavior.

**Assessment**
- Good fit for early-stage, embedded-friendly prototyping where explainability and runtime determinism are preferred.
- Limited robustness to non-stationary lighting, wet-surface highlights, occlusion, and broad defect morphology.

**Audit recommendation**
- Short term: retain calibrated HSV provider as baseline and explicitly characterize operating envelope (lux range, camera gain, exposure lock).
- Medium term: evaluate lightweight detector/segmenter (e.g., MobileNet/YOLO-nano/UNet-lite) only if edge-case false negatives exceed target KPI.

### Data preprocessing and augmentation
**Observed implementation**
- Preprocessing includes lane geometry mapping and calibration conversion from pixels to mm.
- Detection logic uses grayscale thresholding and contour area filtering, with color-threshold classification.

**Gaps**
- No explicit illumination normalization pipeline (e.g., CLAHE, white balancing by reference patch) in deploy path.
- No explicit augmentation framework for synthetic lighting/occlusion/background variation is visible.

**Audit recommendation**
- Add deterministic photometric normalization stage before thresholding.
- Add a reproducible offline augmentation recipe for wet beans, gloss, blur, partial occlusion, and debris.

### Training pipeline and validation strategy
**Observed implementation**
- A train artifact metadata contract exists with score threshold and label space validation.
- Dataset manifest is minimal and indicates placeholder-scale data.

**Gaps**
- No full training pipeline, experiment tracking, or split governance for train/validation/test beyond simple manifest entries.
- No explicit cross-lot/cross-day validation design to represent packhouse variability.

**Audit recommendation**
- Define formal ML lifecycle: data versioning, split policy, model registry, and retraining triggers based on drift or KPI decay.

### Hyperparameter tuning, model updates, thresholding
**Observed implementation**
- Thresholds exist at multiple points: contour min area, color reject thresholds, rule thresholds (`infection_score`, `curve_score`, `size_mm`).
- Training metadata includes `score_threshold` validation.

**Risks**
- Multi-threshold systems can create unstable decision boundaries if not jointly tuned by lot/season.

**Audit recommendation**
- Add threshold calibration protocol with ROC/PR analysis and change-control approval for production updates.

---

## 3) Architecture & Design

### Modular separation
- Separation is clean and reviewable:
  - acquisition/bench sources,
  - CV detection and preprocessing,
  - decision logic/rules,
  - scheduler and serial framing,
  - GUI/operator controls.
- This supports fault isolation and verification at interface boundaries.

### Frameworks and libraries
- Uses Python + OpenCV + NumPy for CV; schema/contracts and protocol layers for deterministic communication.
- No evidence of PyTorch runtime in deployed path; current architecture remains classical CV-centric.

### Scalability, maintainability, real-time constraints
- Strong contract-first design (schemas, protocol constraints, strict bounds).
- Timing budget documentation and hardware-vs-bench evidence indicate active real-time governance.
- Remaining scale risk: production variability may outrun bench assumptions if CV remains threshold-driven without adaptive calibration.

### Code organization and documentation quality
- Documentation quality is strong (architecture, timing budget, compliance matrix, safety evidence).
- Open items are transparently documented (deployment matrix, release gate coupling, hardware ownership).

---

## 4) Data Quality & Dataset Audit

### Dataset description and sufficiency
- Manifest currently lists very small train/eval samples, indicating non-production dataset maturity.
- Defect taxonomy, bean varietal coverage, and lighting strata are not formally specified in dataset artifacts.

### Label correctness and bias
- No visible label QA workflow (inter-annotator agreement, adjudication, spot audits).
- Bias risk is high for lot-specific color tones and seasonal moisture differences.

### Edge-case coverage
- Edge cases requested for this domain (occlusion, wet beans, physical damage, overlap, debris) are not explicitly evidenced in dataset governance artifacts.

### Split adequacy
- Current split evidence is insufficient for production claims.
- Recommend stratified splits across day/night shifts, conveyor lots, and camera positions; preserve temporal holdout for drift detection.

---

## 5) Performance Evaluation

### Metrics coverage
**Strengths**
- System has timing-stage observability and deterministic telemetry across ingest/decision/schedule/transport/cycle stages.
- Hardware readiness timing summary indicates all observed P95/max values are within declared budgets.

**Gaps**
- CV quality metrics (precision/recall/FNR by defect class, confusion matrices) are not provided in current evidence.

### Edge-case performance
- No quantified benchmark found for small defects, overlapping beans, variable lighting, or wet/debris conditions.

### Inference speed and throughput
- Transport and cycle latency tracking is mature and budgeted.
- Throughput to conveyor coupling appears feasible from timing budget pass, but defect-level detection efficacy under production variance remains unproven.

### Baseline/manual comparison
- No documented side-by-side benchmark against manual inspectors or legacy sorter yield.

---

## 6) Mechanical Response Integration

### Actuation timing and synchronization
- Scheduler validates lane and trigger position bounds, supporting deterministic reject positioning.
- Pipeline combines lane ID and calibrated y-position to compute `trigger_mm` offset from camera-to-reject distance.

### Reliability and repeatability
- Protocol and queue semantics include ACK/NACK handling with metadata and retry policy.
- Hardware readiness artifacts indicate parity for SAFE watchdog recovery scenarios.

### Safety mechanisms
- SAFE mode behavior and recovery workflows are implemented/tested in bench and reflected in hardware evidence summaries.
- Queue depth and scheduler state telemetry are part of ACK metadata validation.

### Control-loop latency vs conveyor speed
- Timing evidence reports PASS against budget, but explicit conveyor-speed-to-latency margin calculations should be included in release checklist.

---

## 7) Robustness & Risk Analysis

### Adversarial/harsh operating conditions
- Threshold-based CV is vulnerable to glare, wet surfaces, residue, camera misalignment, and brightness drift.
- Mechanical risk remains for jams and drift in actuator response if feedback sensing is absent or weak.

### Operational risks
- Missed defects (false negatives) are the highest food-quality risk.
- False rejects increase yield loss and operator intervention frequency.
- Transport jitter is bounded in current evidence, but production serial anomalies should be continuously trended.

### Safety, fairness, regulatory (food handling)
- Safety posture (SAFE fallback and watchdog behavior) is positive.
- Regulatory-readiness gap: need formal traceability for defect decisions, calibration history, and maintenance logs suitable for audit/compliance programs.

---

## 8) Testing & Validation

### Unit and integration tests
- Repository includes broad unit/integration coverage across preprocess, detection providers, protocol compliance, scheduling, serial transport, and deterministic telemetry.

### Bench testing
- Bench CLI/GUI and hardware readiness artifacts show mature test discipline for protocol/queue/timing/safety behaviors.

### Continuous monitoring and retraining feedback
- Telemetry foundations exist; however, closed-loop model performance monitoring (per-class drift, false-reject trend alarms, data capture for retraining) is not yet fully formalized.

---

## 9) Deployment & Monitoring

### Deployment environment
- Bench/staging/production concepts are documented, but production deployment matrix and ownership details remain incomplete.

### Monitoring scope
Recommended live monitors:
- defect detection rate by class/lot/shift,
- false reject and miss-confirmation rates,
- queue depth and retry/NACK trends,
- actuator cycle consistency and jam incidence,
- calibration drift indicators.

### Logging, alerting, maintenance
- Protocol and stage telemetry support observability.
- Add maintenance schedule integration for actuator wear, calibration revalidation cadence, and trigger drift checks.

---

## 10) Recommendations

### Short-term (0–8 weeks)
1. **Threshold governance:** Implement controlled threshold tuning with ROC/PR review and signed release notes.
2. **Lighting consistency:** Standardize illumination hardware and lock exposure/gain to reduce drift.
3. **Actuator timing verification:** Add conveyor-speed margin test that validates reject timing under peak throughput.
4. **Defect KPI dashboard:** Publish precision/recall/FNR and false-reject rate by shift.
5. **Dataset QA checklist:** Enforce label audits and edge-case tagging before each model/rule update.

### Long-term (2–6 months)
1. **Dataset expansion:** Increase coverage across bean varieties, seasons, moisture states, and contamination patterns.
2. **Multi-camera coverage:** Reduce occlusion and overlap blind spots.
3. **Predictive maintenance:** Model actuator wear from cycle telemetry and queue stress indicators.
4. **Adaptive CV roadmap:** Evaluate hybrid approach (classical CV + lightweight learned model for hard cases).
5. **Formal MLOps loop:** Automate drift-triggered sampling, retraining, and staged rollback.

### Suggested KPIs
- Throughput (beans/min, packs/hour).
- Defect detection rate (overall + per defect class).
- Rejection accuracy (precision, recall, FPR, FNR).
- Timing margin (decision-to-actuation latency vs conveyor offset budget).
- Unplanned downtime (minutes/day) and jam rate.
- Calibration drift frequency and recovery time.

---

## Final Summary: Key Risks and Top 5 Prioritized Recommendations

### Key risks
- **R1 — CV robustness risk:** threshold-based detection may underperform in real packhouse variability (wet/glare/debris).
- **R2 — Data maturity risk:** current dataset evidence is too limited for production-grade claims.
- **R3 — KPI visibility risk:** absence of comprehensive defect-class metrics can hide failure modes.
- **R4 — Deployment governance risk:** incomplete production matrix and release ownership can delay safe rollout.
- **R5 — Mechanical drift risk:** without explicit long-horizon actuator health analytics, timing precision may degrade silently.

### Top 5 prioritized recommendations
1. Establish production KPI gates (precision/recall/FNR + false reject) before every release.
2. Standardize illumination/camera controls and validate thresholds per lot/shift.
3. Expand and stratify dataset with edge-case-rich labeling and QA audits.
4. Implement conveyor-speed timing margin validation in hardware-in-the-loop acceptance tests.
5. Deploy predictive maintenance + drift monitoring for both CV and actuation subsystems.
