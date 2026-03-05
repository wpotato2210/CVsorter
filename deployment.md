# deployment.md

## Purpose
Define deterministic deployment and operator procedures for the CV runtime modules (`preprocess`, `dataset`, `model`, `train`, `eval`, `infer`, `scheduler`, `actuator_iface`, `config`) with verifiable I/O contracts and safety thresholds.

## Deterministic Runtime Contracts
- Image contract: `(H,W,3)` RGB `uint8` input at runtime.
- Tensor contract: `(B,C,H,W)` `float32` with `C=3`, device = `PipelineConfig.device`.
- Dataset contract: nonempty dataset required before train/eval.
- Timing variables used by scheduler telemetry:
  - `frame_timestamp_ms`
  - `pipeline_latency_ms`
  - `trigger_offset_ms`
  - `actuation_delay_ms`
- Physical thresholds are loaded from `src/coloursorter/config/*` only.

## Acceptance Threshold Evidence
Promotion from bench -> deployment requires evidence artifacts showing all three acceptance checks pass:
- Latency: `pipeline_latency_ms <= config.physical.timing.max_latency_ms`
- Throughput: `throughput_fps >= config.physical.throughput.min_frames_per_second`
- E-STOP response: `estop_response_ms <= config.physical.timing.estop_response_threshold_ms`

Canonical schema references:
- `contracts/pipeline_runtime_config_schema.json`
- `contracts/pipeline_telemetry_schema.json`

## Operator Go/No-Go + Reset Authority Workflow
1. **Go/No-Go owner:** shift operator validates latest acceptance artifact set and confirms all threshold checks are true.
2. **Runtime authority:** operator may issue `GO` only when MCU mode is not `SAFE` and queue depth is within configured bounds.
3. **E-STOP authority:** any operator may issue `ESTOP` immediately.
4. **Reset authority:** lead operator (or designated supervisor) is the sole authority for reset-to-run after E-STOP/SAFE.
5. **Reset prerequisites:**
   - fault cause identified,
   - telemetry confirms threshold compliance,
   - explicit reset approval logged.

## Artifact Traceability Requirements
Each deployment decision must cite immutable artifacts:
- telemetry sample file with `frame_timestamp_ms`, `pipeline_latency_ms`, `trigger_offset_ms`, `actuation_delay_ms`
- acceptance result (latency/throughput/E-STOP pass/fail)
- run configuration snapshot matching `pipeline_runtime_config_schema.json`

Store these under `docs/artifacts/hardware_readiness/` with scenario/date prefix to preserve traceability.
