# Tasks

This file is the single authoritative task list for the repository.

## Core
- [ ] Implement bench/live parity wiring so decision thresholds and fault-context precedence are identical for fixed fixtures.
- [ ] Enforce startup diagnostics as a hard pre-run gate with deterministic failure outputs.
- [ ] Replace synthetic live-capture timestamps with monotonic capture timestamps while preserving deterministic replay timestamp behavior.
- [ ] Finalize deterministic protocol command/ACK vector coverage for HELLO, HEARTBEAT, SET_MODE, SCHED, GET_STATE, and RESET_QUEUE.
- [ ] Build and enforce fixed-seed scheduler timing jitter envelopes for pass/edge/fail windows.

## Hardware
- [ ] Harden deterministic HIL repeatability gate logic and fixtures so repeated fixed runs produce stable verdicts.
- [ ] Expand malformed-frame and NACK-mapping conformance tests for protocol failure detection.
- [ ] Add SAFE-mode invariant stress tests proving no actuation path while SAFE is active and queue ordering remains deterministic.

## Software
- [ ] Codify ingest channel contract as either strict BGR `(H,W,3)` acceptance or deterministic explicit conversion before detection.
- [ ] Replace runtime monkey-patched threshold dependencies with explicit typed interfaces.
- [ ] Prevent implicit `model_stub` usage in integration/live execution paths (fail closed with deterministic errors).
- [ ] Implement bench/live differential trace comparison for fault-injected scenarios with zero-divergence assertions.
- [ ] Add timing-drift regression harness with fixed jitter injection and deterministic envelope checks.

## Testing
- [ ] Add deterministic evidence bundler validation so Phase 3 artifacts are regenerated and committed as valid machine-readable outputs.
- [ ] Automate deterministic rollback drills with dry-run verification and reproducible logs.
- [ ] Add repeated-run flake classification for HIL/regression suites to separate deterministic failures from infra noise.
- [ ] Produce and archive closure evidence by running `pytest tests/`, `pytest bench/`, `run_tests.bat` (where supported), and `pytest --cov=src/coloursorter --cov-report=xml`.

## Cleanup / Tech Debt
- [ ] Keep phase planning docs as context-only references and prevent reintroduction of parallel task checklists outside this file.
- [ ] Normalize stale path references in planning docs to current repository paths when those references are next touched.
- [ ] Resolve ambiguous ownership/milestone metadata for remaining Phase 5 planning artifacts before execution-window approval.
