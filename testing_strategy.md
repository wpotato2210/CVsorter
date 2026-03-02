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
  - Regression protection for scheduler projection `SCHED:<lane>:<position_mm>`, SAFE mode behavior, retry semantics, and malformed frame handling.

## Terminology Alignment (protocol + architecture)
- Assertions and fixtures should use protocol-native command/state labels and canonical NACK details.
- Layered suites should map directly to architecture flow: preprocess/calibration -> deploy/eval -> scheduler -> transport.

## States
- Test stage state: `unit | integration | bench_e2e`.
- Runtime mode test matrix: `AUTO | MANUAL | SAFE`.
- Queue depth test matrix: `empty | partial | full`.

## Dependencies
- `tests/` suite and fixtures.
- `protocol.md` ACK/NACK behavior and transition policy.
- `architecture.md` pipeline ordering and module boundaries.
- `threading_model.md` concurrency invariants for ordering, atomicity, and BUSY publication.

## Key Behaviors / Invariants
- Unit tests validate deterministic transforms from frame input to decision payload.
- Protocol tests assert command arg bounds, frame parsing, and canonical NACK code mapping.
- State tests assert `SAFE -> AUTO` rejection and queue-clear side effects on mode change/`RESET_QUEUE`.
- Scheduler/serial integration tests assert canonical scheduler projection and correct wire-frame encoding.
- Retry tests assert timeout/retry/backoff behavior (`100 ms`, max `3`).

## Cross-layer Dependency Notes
- `constraints.md` provides numeric bounds and transition rules to validate.
- `error_model.md` provides expected recovery actions to assert during negative-path tests.
- `security_model.md` provides malformed/flood/throttle policies to verify.
- `deployment.md` should define staging/production parity checks reusing this matrix.

## Performance / Concurrency Notes
- Insufficient stress tests can hide queue contention and BUSY behavior under burst triggers.
- Bench-only traffic patterns may not expose worst-case concurrent frame + command load.
- Flaky timing tests can produce non-deterministic results if wall-clock assumptions are strict.

## Open Questions (requires input)
- Minimum coverage targets by module area (CV, scheduler, transport, GUI/bench integration).
- Whether stress benches must simulate maximum load (frame bursts + command bursts + retry storms).
- Whether long-running soak and concurrency edge-case suites are required for release gating.
- Which execution model assumptions (single-threaded vs concurrent producers) must be tested as release blockers.

## Conflicts / Missing Links
- Hardware-in-the-loop tests for MCU and servo timing are not yet defined.
