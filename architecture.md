# architecture.md

## System architecture (current build state)

### Layered modules
1. **Input/Contracts**
   - Schemas and protocol contracts: `contracts/`, `protocol/`, `data/`.
   - Runtime configs: `configs/`.
2. **Core CV pipeline**
   - Preprocess: `src/coloursorter/preprocess/lane_segmentation.py`
   - Calibration mapping: `src/coloursorter/calibration/mapping.py`
   - Model contract types: `src/coloursorter/model/types.py`
   - Rule evaluation: `src/coloursorter/eval/rules.py`
   - Deploy orchestration: `src/coloursorter/deploy/pipeline.py`
3. **Actuation + transport**
   - Scheduler: `src/coloursorter/scheduler/output.py`
   - Serial wire/adapter: `src/coloursorter/serial_interface/*`
4. **Bench simulation + operator UX**
   - Bench execution and sources: `src/coloursorter/bench/*`
   - GUI: `gui/bench_app/*`

## Dataflow with explicit I/O/dependencies
```mermaid
flowchart LR
    F[Input\nI: FrameMetadata,ObjectDetection[]\nDep: frame source] --> L[Lane segmentation\nO: lane_id\nDep: lane_geometry.yaml]
    F --> M[Calibration mapping\nO: px_to_mm\nDep: calibration.json]
    L --> P[Deploy pipeline\nI: lane_id + class + mm\nO: DecisionPayload]
    M --> P
    P --> E[Eval rules\nO: reject_reason\nDep: thresholds/config]
    E --> P
    P --> S[Scheduler\nO: ScheduledCommand\nDep: scheduling policy]
    S --> W[Serial wire\nO: SCHED:<lane>:<position_mm>\nDep: MCU command contract]
```

## Runtime surfaces
- **CLI bench mode**: deterministic scenario validation and transport simulation.
- **GUI bench mode**: operator-facing telemetry, queue depth, and safe-state visibility.

## Quality gates reflected in repository
- Unit/integration tests under `tests/` for preprocess, scheduler, serial interface, camera/config/runtime behavior.
- OpenSpec mirror and migration notes under `docs/openspec/` and `docs/*migration*.md`.
