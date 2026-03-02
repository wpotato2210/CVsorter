# threading.md

## Scope
Reverse-engineered bench runtime threading/concurrency model for ChatGPT edits.

## Frozen I/O
### Input events
- Qt UI actions (`Replay`, `Live`, `Home`, serial connect/disconnect, manual fire)
- Cycle timer timeout (`QTimer.timeout`)
- Frame source reads (replay/live)
- Transport responses/errors

### Output events
- Frame preview updates
- Lane overlay updates
- Queue/fault state updates
- Log row emissions

## Dependencies
- Controller/event loop: `gui/bench_app/controller.py`
- Main window/UI plumbing: `gui/bench_app/app.py`
- Bench cycle execution: `src/coloursorter/bench/runner.py`
- Transport implementations: `src/coloursorter/bench/mock_transport.py`, `src/coloursorter/bench/serial_transport.py`

## Runtime model
- Single Qt main-thread orchestration (`QApplication` event loop).
- No explicit `threading.Thread` and no `QThread` worker pipeline in current implementation.
- Periodic work is timer-driven (`_cycle_timer`) using configured cycle period.
- Controller state transitions are governed by `QStateMachine` via `BenchControllerStateMachine`.

## Named variables (controller critical)
- `runtime_state.controller_state`: `idle|replay_running|live_running|faulted|safe`
- `runtime_state.operator_mode`: `AUTO|MANUAL|SAFE`
- `runtime_state.scheduler_state`: host scheduler projection (`IDLE|ACTIVE`)
- `cycle_config.period_ms`: timer cadence
- `cycle_config.queue_consumption_policy`: `none|one_per_tick|all`

## Tick execution order
1. timer tick enters `_on_cycle_tick`
2. frame acquisition + decode path
3. `BenchRunner.run_cycle` (decision/schedule/transport roundtrip)
4. protocol/transport response reconciliation
5. Qt signal emission to UI widgets/log table

## Edit constraints
- Preserve deterministic tick ordering and state-machine transitions.
- Do not introduce blocking work in timer handlers unless moved behind an explicit worker boundary.
- Keep protocol mode changes command-driven (host authority), not GUI-local mutation.
