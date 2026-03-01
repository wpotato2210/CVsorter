# Bench Mode I/O and Dependencies

```text
[ReplayFrameSource]
  I/O: source path -> BenchFrame(frame_id,timestamp,image)
  deps: cv2, filesystem/video codec
        |
        v
[PipelineRunner]
  I/O: FrameMetadata + ObjectDetection -> DecisionPayload + ScheduledCommand
  deps: preprocess.lane_segmentation, calibration.mapping, eval.rules
        |
        v
[VirtualEncoder]
  I/O: (start_ts,end_ts) -> pulses
  deps: EncoderConfig, EncoderFaultConfig
        |
        v
[BenchRunner]
  I/O: frame+detections+pulses -> BenchLogEntry
  deps: PipelineRunner, MockMcuTransport, VirtualEncoder
        |
        v
[MockMcuTransport]
  I/O: ScheduledCommand -> TransportResponse(ACK/NACK,queue_depth,RTT)
  deps: scheduler.output, bench fault state
        |
        v
[Qt Bench App]
  panels: live preview | lane overlay | queue depth/state | mode/homing | SAFE/watchdog | telemetry log
  I/O: BenchLogEntry stream -> table rows and status labels
  deps: PySide6, coloursorter.bench

Note: Serial transport now exposes stable queue observability accessors (`transport_queue_depth`, `transport_last_queue_cleared`) so controller queue-state signals can report real queue depth/clear observations in serial mode.
```

## Pass/Fail scenarios

| Scenario | Pass condition |
|---|---|
| nominal | avg RTT <= 12 ms and peak RTT <= 25 ms |
| latency_stress | avg RTT <= 25 ms and peak RTT <= 60 ms |
| fault_to_safe | at least one SAFE transition observed |
| recovery_flow | SAFE transition observed and later ACK recovery |
