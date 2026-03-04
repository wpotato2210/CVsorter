# Technical Review Artifact — Optical Sensing & Classification System

## 1) Project Overview

### Purpose
- This review artifact is limited to optical sensing, calibration, classification, recipe management, operator roles, alarms, and logs.
- The goal is to confirm software readiness for vision-driven quality classification workflows in a bench-first environment.

### Scope
- In-scope capability domains (and only these domains):
  - optical sensing pipeline behavior,
  - calibration data and mapping integrity,
  - classification logic and threshold governance,
  - recipe definition and controlled updates,
  - role-based operational controls,
  - alarm semantics and operator signaling,
  - logging and auditability.

### Out of Scope
- Excluded topics:
  - all physical rejection/actuation behavior,
  - reject timing topics (trigger/schedule/mechanical-window timing),
  - reject-channel testing topics,
  - reject mode logic and actuation command transport topics.
- Rationale:
  - the target machine architecture for this review differs from the actuation architecture represented elsewhere in the repository,
  - therefore this artifact intentionally excludes rejection/actuation requirements and evaluates only architecture-compatible optical/decision-layer requirements.

---

## 2) Requirement Review (Optical/Decision Layer Only)

## 2.1 Optical sensing
- Frame ingestion path is present and structured for deterministic processing.
- Detection providers are implemented with explainable OpenCV-based pipelines suitable for controlled lighting baselines.
- Current risk remains sensitivity to illumination variance, glare, and contamination.

## 2.2 Calibration
- Calibration mapping and lane geometry contracts are clearly represented in config/schema artifacts.
- Pixel-to-mm mapping integrity checks are present at config/contract boundaries.
- Recommended control: explicit recalibration cadence with operator acknowledgment logging.

## 2.3 Classification
- Classification decisions are rule/threshold-driven and reviewable.
- Decision thresholds exist for defect-related dimensions and can be governed through controlled updates.
- Recommended control: formal threshold change workflow with before/after KPI comparison.

## 2.4 Recipes
- Recipe-like configuration behavior is represented through structured runtime/config artifacts.
- Recommended control: versioned recipe IDs, approval metadata, and rollback reference in logs.

## 2.5 Roles
- Operator and control-surface behaviors are represented via mode/state handling concepts.
- Recommended control: explicit role matrix for who can edit calibration, thresholds, and recipes.

## 2.6 Alarms
- Safety/fault signaling patterns are documented and testable in bench workflows.
- Recommended control: classify alarms by severity and required operator response, then enforce acknowledgment logging.

## 2.7 Logs
- Telemetry/log structures are strong and already used for readiness evidence.
- Recommended control: enforce immutable audit fields for recipe version, calibration version, role/user action, and alarm acknowledgments.

---

## 3) Findings Summary

### Strengths
- Clear contract-first architecture for optical decision flow.
- Good documentation coverage for configs, schemas, and telemetry artifacts.
- Bench validation discipline supports repeatable evidence capture.

### Gaps
- Dataset maturity and variability coverage are still below production-grade confidence.
- Optical robustness under real-world lighting drift needs stronger normalization/monitoring controls.
- Governance for recipe/threshold/role changes should be made explicit and auditable.

---

## 4) Prioritized Recommendations

1. Define and enforce a formal optical calibration SOP (frequency, tolerances, sign-off, log fields).
2. Add classification KPI gates per recipe (precision/recall/FNR/FPR) and require gate pass before promotion.
3. Introduce explicit role-based permissions for calibration edits, recipe edits, and alarm overrides.
4. Standardize alarm taxonomy (severity, response SLA, escalation path) and enforce acknowledgment audit trails.
5. Expand dataset and validation strata across lots, lighting conditions, and contamination states.

---

## 5) Acceptance Criteria for This Artifact

This review is considered satisfied when all tracked requirements remain limited to:
- optical sensing,
- calibration,
- classification,
- recipes,
- roles,
- alarms,
- logs.

Any requirement involving physical rejection/actuation (including timing, channel tests, or reject mode logic) is explicitly out of scope for this artifact.
