# OpenSpec v3 Data Annotation Specification

## 1) Annotation schema

Annotation records MUST be stored as JSON lines (`.jsonl`) where each line represents one object instance tied to one frame.

### 1.1 Required top-level fields
- `annotation_id` (string, UUIDv7): unique annotation row identifier.
- `annotation_version` (string): schema version, MUST be `v3.0` for this spec.
- `capture_id` (string): immutable ID for a capture session.
- `frame_id` (string): immutable ID for a frame in `capture_id`.
- `object_id` (string): per-frame stable object key (e.g., `obj_0001`).
- `class_label` (string): one of the classes in §1.2.
- `defect_tags` (array[string]): zero or more tags from §1.3.
- `geometry` (object): coordinates following §1.4.
- `occlusion` (object): occlusion flags from §1.5.
- `grade_label` (string): one of the grades in §1.6.
- `annotator_id` (string): human or service principal who created the label.
- `annotated_at` (string, RFC 3339 UTC timestamp): creation timestamp.
- `qa_status` (string): `pending`, `accepted`, `rework_required`, or `adjudicated`.
- `traceability` (object): linkage keys in §6.

### 1.2 Class ontology
`class_label` MUST be one of:
- `bean_ok`
- `bean_discolored`
- `bean_broken`
- `bean_foreign_material`
- `bean_clump`

Class additions are allowed only via schema minor version bump (`v3.x`). Removal or semantic redefinition requires a major version (`v4.0+`).

### 1.3 Defect tags
`defect_tags` MUST contain only allowed tags:
- `crack`
- `chip`
- `mold_spot`
- `burn_mark`
- `insect_damage`
- `foreign_fiber`
- `foreign_stone`
- `paint_or_plastic`
- `multi_bean_overlap`
- `surface_contamination`

Rules:
- `bean_ok` MUST use an empty `defect_tags` array.
- Non-`bean_ok` classes SHOULD include at least one semantically aligned tag.
- `defect_tags` MUST NOT include duplicate values.

### 1.4 Coordinate system and geometry
All coordinates MUST be image-plane pixel coordinates with origin at the top-left:
- `x` increases left-to-right.
- `y` increases top-to-bottom.

`geometry` object MUST include:
- `image_width_px` (int > 0)
- `image_height_px` (int > 0)
- `bbox_xywh` (array[4], float): `[x_min, y_min, width, height]` in pixels.
- `segmentation` (array[array[2]], optional): polygon vertices in clockwise order.
- `centroid_xy` (array[2], float): centroid in pixels.
- `lane_index` (int >= 0): lane index at annotation time.

Validation rules:
- `0 <= x_min < image_width_px`, `0 <= y_min < image_height_px`.
- `width > 0`, `height > 0`.
- `x_min + width <= image_width_px`, `y_min + height <= image_height_px`.
- If `segmentation` is present, every point MUST be in image bounds.

### 1.5 Occlusion flags
`occlusion` MUST include:
- `is_occluded` (bool)
- `occlusion_ratio` (float in `[0.0, 1.0]`)
- `occluded_by` (string enum): `none`, `bean`, `foreign_material`, `hardware_shadow`, `motion_blur`

Rules:
- If `is_occluded = false`, `occlusion_ratio` MUST be `0.0` and `occluded_by = none`.
- If `is_occluded = true`, `occlusion_ratio` MUST be `> 0.0`.

### 1.6 Grading labels
`grade_label` is a quality/rejection stratification independent from class:
- `grade_a` (production pass)
- `grade_b` (degraded but acceptable)
- `reject_minor`
- `reject_major`
- `reject_critical`

Rules:
- `bean_ok` MUST be `grade_a` or `grade_b` only.
- Any `bean_foreign_material` instance MUST be `reject_major` or `reject_critical`.

## 2) Dataset minimums and imbalance policy

Minimum accepted dataset size for model promotion:
- Global minimum object instances: `>= 60,000`.
- Per-class minimum object instances:
  - `bean_ok`: `>= 20,000`
  - `bean_discolored`: `>= 8,000`
  - `bean_broken`: `>= 8,000`
  - `bean_foreign_material`: `>= 6,000`
  - `bean_clump`: `>= 6,000`

Split constraints (by `capture_id` to avoid leakage):
- Train: 70%
- Validation: 15%
- Test: 15%

Per-class floor in each split:
- Validation and test MUST each contain at least 800 samples per non-majority class.
- If a class cannot satisfy floor, promotion is blocked and targeted collection is required.

Class-imbalance policy:
- Maximum class ratio (majority:minority) in training data MUST be `<= 4:1` after rebalancing.
- Rebalancing order of preference:
  1. Targeted collection from production-like captures.
  2. Loss weighting (`effective_num_samples` or focal weighting).
  3. Controlled oversampling of minority classes (max 2.5x replication factor).
- Pure duplication oversampling beyond 2.5x is prohibited.

## 3) Active learning sampling and retraining triggers

### 3.1 Sampling rules
Active learning queue SHOULD be refreshed daily and MUST prioritize:
1. **High uncertainty:** top 20% entropy or lowest confidence margin.
2. **Disagreement set:** model-vs-rules disagreement and ensemble disagreement.
3. **Rare contexts:** underrepresented lane, lighting profile, speed profile, and hardware configuration.
4. **Near-miss defects:** predictions within 0.1 score margin around reject thresholds.

Sampling composition per refresh:
- 40% uncertainty
- 30% disagreement
- 20% rare contexts
- 10% random baseline

Deduplication:
- Perceptual hash distance threshold MUST suppress near-duplicates in one batch.
- Same `capture_id` contribution capped at 15% of any one labeling batch.

### 3.2 Retraining triggers
Retraining MUST be triggered when any condition is met:
- `>= 8,000` newly QA-accepted labels accumulated since last train.
- Any critical class (`bean_foreign_material`, `bean_clump`) recall on shadow validation drops by `>= 2.5` absolute points.
- Population stability index (PSI) of key embedding features exceeds `0.25` for 3 consecutive days.
- Production adjudication backlog exceeds 1,500 items for 5 business days.

Emergency retraining trigger:
- If `reject_critical` false-negative rate exceeds 0.5% over rolling 24h, start expedited retraining and hotfix review within 4 hours.

## 4) Synthetic data augmentation policy

Synthetic data is allowed only to improve robustness, not replace real defect evidence.

Hard limits:
- Synthetic objects MUST NOT exceed 30% of training set for any class.
- For `bean_foreign_material`, at least 80% of training samples MUST remain real-world captures.

Allowed techniques:
- Photometric shifts bounded to measured camera variance.
- Motion blur and noise profiles calibrated from bench telemetry.
- Physically plausible occlusion compositing.
- Domain randomization constrained by lane geometry and belt kinematics.

Realism safeguards:
- Synthetic generation parameters MUST be versioned and linked to calibration baselines.
- A realism gate model (real vs synthetic discriminator) MUST have AUC <= 0.80; if higher, synthetic artifacts are considered too separable and must be revised.
- Human reviewer spot-check of at least 200 synthetic samples per training cycle.

Leakage safeguards:
- No synthetic sample may be generated from validation/test source frames.
- Split assignment MUST occur before synthesis and be inherited by descendants.
- Hash-based lineage (`parent_frame_hash`, `transform_chain_hash`) MUST be recorded for every synthetic instance.

## 5) Label QA metrics and adjudication workflow

### 5.1 QA metrics and thresholds
Mandatory metrics per weekly QA report:
- Inter-annotator agreement (IAA):
  - Class label Cohen's kappa: `>= 0.85`
  - Grade label weighted kappa: `>= 0.80`
  - Defect tag micro-F1 across annotator pairs: `>= 0.82`
- Geometric consistency:
  - Bounding box IoU (annotator pair median): `>= 0.75`
  - Centroid distance p95: `<= 6 px`
- Process quality:
  - Rework rate: `<= 7%`
  - Critical error escape rate (found post-release): `<= 0.2%`

Breach policy:
- Any two consecutive weekly breaches on the same metric MUST trigger retraining of annotators and temporary 100% secondary review on impacted class/task.

### 5.2 Adjudication workflow
1. **Double-labeling:** minimum 10% random sample and 100% of active-learning critical queue are dual-annotated.
2. **Conflict detection:** automatic flag on class mismatch, grade mismatch, tag mismatch, or IoU < 0.6.
3. **Adjudicator review:** senior reviewer resolves conflict within 2 business days.
4. **Root-cause coding:** adjudicator records reason code (`guideline_gap`, `tooling_issue`, `human_error`, `ambiguous_visual`).
5. **Feedback loop:** update annotation guide and conduct targeted refresher within 7 days for recurring codes.
6. **Audit trail:** all decisions are immutable append-only events with actor and timestamp.

## 6) Traceability keys for telemetry and audit linkage

Each annotation record MUST include a `traceability` object with:
- `production_event_id` (string): ID from runtime decision event.
- `telemetry_record_id` (string): ID tying to bench/runtime telemetry log row.
- `audit_case_id` (string, optional): incident/adjudication case key.
- `model_version_inference` (string): model version that produced original prediction.
- `pipeline_config_hash` (string): hash of deploy/runtime config at inference time.
- `camera_id` (string): hardware source identifier.
- `lane_index` (int): copied from runtime context.
- `capture_timestamp_utc` (RFC 3339): source frame capture time.
- `data_retention_tier` (string enum): `hot`, `warm`, `cold`.

Integrity requirements:
- `production_event_id` + `telemetry_record_id` pair MUST be unique per annotation.
- Traceability fields MUST be non-null for production-derived samples.
- Joinability to telemetry and audit datasets MUST be validated in ingestion CI before dataset release.

## Governance and change control
- This spec is normative for OpenSpec v3 data annotation operations.
- Proposed updates require approval from CV lead, QA lead, and manufacturing quality owner.
- Any threshold change MUST include backtest evidence on at least one full historical quarter.
