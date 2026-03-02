# threading_model.md

## Purpose
Define concurrency ownership and synchronization rules for frame ingestion, CV processing, queue mutation, and MCU transport to prevent races and nondeterministic trigger behavior.

## Inputs / Outputs
- **Inputs**
  - Frame stream events from camera/bench source.
  - Command events (`SCHED`, mode changes, queue reset).
  - Transport ACK/NACK and timeout events.
- **Outputs**
  - Serialized state transitions for mode, queue depth, and scheduler state.
  - Deterministic trigger dispatch ordering to MCU.

## States
- Worker roles: `frame_producer`, `pipeline_worker`, `scheduler_dispatcher`, `transport_io`.
- Shared states: `mode`, `queue_depth`, `scheduler_state`, `busy_flag`.
- Lifecycle states: `startup | running | draining | stopped`.

## Dependencies
- `architecture.md` runtime surfaces and module decomposition.
- `protocol.md` BUSY/QUEUE_FULL semantics and retry behavior.
- Scheduler and serial interface implementations under `src/coloursorter/*`.

## Key Behaviors / Invariants
- Queue mutation must be single-writer or protected by strict synchronization.
- Trigger dispatch order must preserve enqueue order for equal-priority entries.
- Mode transitions are atomic with respect to queue clear and scheduler state update.
- Frame processing must not block transport ACK handling.
- Busy state publication must be consistent across CLI/GUI telemetry.

## Performance / Concurrency Risks
- Lock contention between frame processing and scheduler mutation can increase frame latency.
- Unbounded queues/channels can cause memory growth under transport stalls.
- Retry timers competing with new outbound triggers can reorder transmissions without explicit sequencing.

## Integration Points
- Camera/bench frame source components.
- Deploy/eval pipeline and scheduler output modules.
- Serial transport loop and protocol response handlers.

## Conflicts / Missing Links
- The exact thread/task model (threads vs async event loop) is not yet declared.
- No hard latency SLO currently links frame ingestion to trigger dispatch completion.
