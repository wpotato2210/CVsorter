# threading.md

## Scope
Reverse-engineered runtime concurrency/threading model from:
- `gui/bench_app/controller.py`
- `gui/bench_app/app.py`
- `src/coloursorter/bench/*`

## Concurrency model summary
- No explicit Python `threading.Thread` or Qt `QThread` worker model in current code.
- GUI execution is event-loop driven via Qt main thread (`QApplication`).
- Repeated processing uses `QTimer` ticks (`_cycle_timer`) in controller.
- Controller lifecycle/state is modeled by `QStateMachine` (`BenchControllerStateMachine`).

## Execution flow per tick
1. Timer timeout triggers controller cycle handler.
2. Frame source pull (live/replay).
3. Pipeline decision + scheduling (`BenchRunner.run_cycle`).
4. Transport send/response handling.
5. UI signals emitted to update preview, queue state, fault state, and logs.

## Implications for ChatGPT edits
- Assume mostly single-threaded UI + I/O orchestration.
- Avoid long/blocking operations in timer callbacks unless moved to worker model.
- Keep state transitions deterministic and explicit in state-machine wiring.
- Serial transport errors are propagated/handled in controller flow; preserve this path.

## Known async boundaries
- Qt signal/slot dispatch points.
- Timer-triggered cycle cadence.
- Serial device response wait in transport layer (timeout/retry behavior).
