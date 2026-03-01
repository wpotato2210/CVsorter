# ColourSorter Pipeline I/O + Dependencies

```mermaid
flowchart LR
    A[Input: FrameMetadata + ObjectDetection[]] --> B[preprocess/lane_segmentation\nI: centroid_x_px + lane_geometry.yaml\nO: lane index]
    A --> C[calibration/mapping\nI: calibration.json\nO: px->mm converter]
    B --> D[deploy/pipeline\nI: lane + px->mm + classification\nO: DecisionPayload[]]
    C --> D
    D --> E[eval/rules\nI: classification\nO: rejection_reason]
    E --> D
    D --> F[scheduler/output\nI: lane + trigger_mm\nO: ScheduledCommand]
    F --> G[serial_interface/wire\nI: ScheduledCommand\nO: SCHED:<lane>:<position_mm>]
```
