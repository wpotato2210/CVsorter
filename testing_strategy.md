# testing_strategy.md

## Purpose
Define layered test coverage that verifies correctness of frame processing, queue behavior, mode transitions, and MCU command emission under deterministic and stressed bench scenarios.

## Inputs / Outputs
- **Inputs**
  - Contracts and protocol artifacts (`contracts/*.json`, `protocol/commands.json`).
  - Runtime modules in preprocess/deploy/eval/scheduler/serial_interface.
  - Bench runtime configs and synthetic frame streams.
- **Outputs**
  - Pass/fail evidence for CV pipeline correctness, protocol conformance, and queue/state invariants.
  - Regression protection for `SCHED:<lane>:<position_mm>`, SAFE mode behavior, retry semantics, and malformed frame handling.

## States
- Test stage state: `unit | integration | bench_e2e`.
- Runtime mode test matrix: `AUTO | MANUAL | SAFE`.
- Queue depth test matrix: `empty | partial | full`.

## Dependencies
- `tests/` suite and fixtures.
- `protocol.md` ACK/NACK behavior and transition policy.
- `architecture.md` pipeline ordering and module boundaries.

## Key Behaviors / Invariants
- Unit tests validate deterministic transforms from frame input to decision payload.
- Protocol tests assert command arg bounds, frame parsing, and canonical NACK code mapping.
- State tests assert `SAFE -> AUTO` rejection and queue-clear side effects on mode change/`RESET_QUEUE`.
- Scheduler/serial integration tests assert canonical `SCHED:<lane>:<position_mm>` emission.
- Retry tests assert timeout/retry/backoff behavior (`100 ms`, max `3`).

## Performance / Concurrency Risks
- Insufficient stress tests can hide queue contention and BUSY behavior under burst triggers.
- Bench-only traffic patterns may not expose worst-case concurrent frame + command load.
- Flaky timing tests can produce non-deterministic results if wall-clock assumptions are strict.

## Integration Points
- CI pipeline gating for unit/integration suites.
- Bench CLI and GUI smoke tests to validate telemetry/state alignment.
- OpenSpec parity checks against runtime contract mirrors.

## Conflicts / Missing Links
- Required minimum coverage thresholds are not yet formalized.
- Hardware-in-the-loop tests for MCU and servo timing are not yet defined.
