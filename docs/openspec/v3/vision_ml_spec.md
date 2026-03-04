# Vision & ML Specification (OpenSpec v3)

## Purpose
This document defines the minimum computer-vision and machine-learning requirements for OpenSpec v3 image understanding pipelines used in CVsorter deployments. It standardizes metadata capture, preprocessing behavior, model packaging, deployment topology, and per-decision explainability outputs.

## 1) Required Frame Metadata Schema Fields
Every captured and processed frame **must** include the following metadata fields to ensure reproducibility, debugging, and model-quality monitoring:

- **Exposure**
  - Captured exposure value(s) applied at acquisition time (for example: exposure time, auto/manual mode, and effective integration).
- **Gain**
  - Sensor gain setting(s), including whether analog or digital gain was applied.
- **Lighting state**
  - Illumination context and control state (for example: strobe on/off, duty cycle, intensity profile, color temperature where available).
- **Camera pose**
  - Pose description relative to conveyor/world reference frame (position + orientation, and calibration revision identifier when available).
- **Conveyor speed**
  - Instantaneous and/or sampled speed context associated with frame capture.
- **Timestamp provenance**
  - Timestamp value and source provenance (sensor clock, host clock, synchronized source), including timezone or monotonic clock semantics as applicable.

Implementations should align extensions and field naming with the canonical frame contract in:

- `docs/openspec/v3/contracts/frame_schema.json`

Where additional deployment-specific metadata is needed, teams should extend schema definitions in a backward-compatible way while preserving required fields and semantics.

## 2) Preprocessing Contract
To reduce train/serve skew and ensure deterministic behavior across hardware targets, preprocessing stages must follow this order:

1. **Color correction**
   - Apply sensor/profile correction first (for example, white balance normalization, color matrix correction, and optional gamma linearization policy).
2. **Geometric undistortion**
   - Apply intrinsic/extrinsic camera correction and lens undistortion in the corrected color space output from step 1.
3. **Normalization**
   - Apply model-input normalization last (resize/crop policy, channel scaling, mean/std normalization, datatype conversion, and tensor layout transformation).

### Contract Rules
- Stage ordering is mandatory: **color correction → geometric undistortion → normalization**.
- Parameters used at runtime must be traceable via versioned configuration artifacts.
- Any deviation from this ordering requires explicit model-version compatibility documentation and validation evidence.

## 3) Model Packaging Guidance
### Canonical artifact
- **ONNX is the canonical interchange format** for OpenSpec v3 model publication.
- Canonical ONNX packages should include:
  - Opset/version declaration
  - Input/output tensor signatures
  - Class/label mapping metadata
  - Preprocessing/postprocessing compatibility notes

### Target-specific conversion notes
- **TensorRT**
  - Convert from canonical ONNX with explicit precision policy (FP32/FP16/INT8).
  - Maintain calibration artifacts for INT8 and record engine build settings for reproducibility.
- **OpenVINO**
  - Use ONNX-to-IR conversion with pinned toolchain version.
  - Preserve input layout assumptions and document any precision fallback behavior.
- **TF Lite**
  - Convert through supported ONNX interoperability path with explicit quantization configuration.
  - Record delegate/runtime assumptions and any operator substitutions introduced during conversion.

All target binaries must preserve semantic parity with canonical ONNX outputs within documented tolerance bounds.

## 4) Deployment Profiles
### Edge-only
- Inference, decisioning, and telemetry aggregation run entirely on edge hardware.
- Suitable for low-latency and intermittent-connectivity environments.

### Edge + cloud
- Primary inference at edge with cloud-assisted analytics, fleet monitoring, and model lifecycle services.
- Supports centralized observability and coordinated model rollout.

### Hybrid retraining workflows
- Edge produces curated datasets and drift/quality signals.
- Cloud handles periodic retraining/validation and publishes signed model updates.
- Edge performs staged deployment (shadow/canary/full rollout) with rollback policy.

## 5) Per-decision Explainability Outputs
Each classification/sorting decision should emit explainability artifacts and structured diagnostics:

- **Saliency or bounding overlays**
  - Visual attribution output aligned with the source frame.
- **Confidence score**
  - Machine-consumable confidence value (and calibrated score where available).
- **Machine-readable reasoning tags**
  - Structured tags describing principal decision factors (for example: feature_presence, occlusion_detected, low_light_condition).

Explainability outputs should be retained according to system policy for auditability, debugging, and model governance.

## 6) Schema Extension Alignment Reference
For frame metadata compatibility and extension strategy, implementers must reference:

- `docs/openspec/v3/contracts/frame_schema.json`

Schema updates should remain backward compatible where possible and include migration notes for downstream consumers.
