# threading_model.md

## Purpose
Define concurrency ownership and synchronization rules for frame ingestion, CV processing, queue mutation, and MCU transport to prevent races and nondeterministic trigger behavior.

## Inputs / Outputs
- **Inputs**
  - Frame stream events from camera/bench source.
  - Command events (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`).
  - Transport ACK/NACK and timeout events.
- **Outputs**
  - Serialized state transitions for `mode`, `queue_depth`, and `scheduler_state`.
  - Deterministic trigger dispatch ordering to MCU in canonical `SCHED:<lane>:<position_mm>` form.

## States
- Worker roles: `frame_producer`, `pipeline_worker`, `scheduler_dispatcher`, `transport_io`.
- Shared states: `mode`, `queue_depth`, `scheduler_state`, `busy_flag`.
- Lifecycle states: `startup | running | draining | stopped`.

## Dependencies
- `architecture.md` runtime surfaces and module decomposition.
- `protocol.md` BUSY/QUEUE_FULL semantics and retry behavior.
- `state_model.md` mode/scheduler/queue transition semantics.
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

## Cross-layer dependency notes
- Correctness constraints in `constraints.md` depend on deterministic queue synchronization and dispatch ordering.
- `error_model.md` retry/failure behavior depends on transport handler isolation from frame-processing work.
- `security_model.md` abuse counters/throttling depend on atomic shared-counter updates.
- `deployment.md` service topology must preserve the same serialization guarantees across bench/staging/production.

## Terminology alignment check
- Uses canonical protocol terms (`SCHED`, `SAFE`, `queue`, `ACK/NACK`, `MCU`) matching `protocol.md`.
- Uses CV pipeline and scheduler terminology matching `architecture.md`.

## Conflicts / Missing Links
- **Requires input:** execution model is not explicit in runtime docs/code contracts (`OS threads`, `async tasks`, or hybrid).
- **Requires input:** transition timing semantics are unspecified for mode changes under load (immediate vs queue-drain boundaries).
- No hard latency SLO currently links frame ingestion to trigger dispatch completion.
