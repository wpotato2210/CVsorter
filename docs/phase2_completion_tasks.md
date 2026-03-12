# Phase 2 Completion Tasks and Success Checks

This checklist translates current integration findings into executable Phase 2 closure work.

## Current status snapshot

- Task-level Phase 2 guardrail tests (`task7`, `task10`-`task28`) are present and should remain green as baseline verification.
- Phase 2 sign-off is still blocked by bench/live integration parity and startup gating gaps.

## Workstream A — Bench/Live behavioral parity (HIGH)

### A1. Pass runtime thresholds and fault context through bench runner
**Goal:** Ensure bench decisions use the same threshold and capture-fault context path as live runtime.

**Implementation tasks:**
1. Add/extend bench runner wiring so `PipelineRunner.run(...)` receives the same threshold + fault context inputs used by live runtime.
2. Add deterministic tests in `tests/` proving identical decision/reason outputs between bench and live paths for fixed fixtures.
3. Add a regression test for fault-context precedence (capture fault overrides when contract requires).

**Success checks:**
- For equivalent inputs, bench and live produce byte-stable decision payloads.
- No divergence in rejection reason codes under threshold-boundary and fault-injected scenarios.

### A2. Enforce startup diagnostics as a hard gate in live runtime
**Goal:** Prevent runtime loop from starting if startup diagnostics fail.

**Implementation tasks:**
1. Add explicit fail-fast path when startup diagnostics are not all-pass.
2. Emit structured deterministic failure output (stable message/code fields).
3. Add tests proving runtime loop does not execute when diagnostics fail.

**Success checks:**
- Startup failures terminate run deterministically before first frame cycle.
- Integration tests verify no transport send occurs after failed diagnostics.

## Workstream B — Timebase and boundary contract integrity (MEDIUM)

### B1. Use real monotonic timestamps for live frame capture
**Goal:** Make live timing diagnostics reflect actual capture cadence.

**Implementation tasks:**
1. Replace synthetic timestamp generation in live source with monotonic capture timestamping.
2. Keep replay source deterministic behavior unchanged.
3. Add tests validating monotonic non-decreasing capture timestamps and deterministic replay behavior.

**Success checks:**
- Live source timestamps track capture-time monotonic clock.
- Replay source remains deterministic for repeated runs.

### B2. Tighten ingest channel contract to BGR `(H,W,3)` or add explicit conversion
**Goal:** Align ingest boundary acceptance with downstream detector expectations.

**Implementation tasks:**
1. Choose one contract path:
   - strict accept-only 3 channels, or
   - deterministic explicit conversion before detection.
2. Add tests for accepted/rejected channel counts and deterministic error messaging.
3. Document the chosen behavior in runtime-facing docs.

**Success checks:**
- No payload can pass ingest and fail later solely due to channel-count mismatch.
- Contract behavior is deterministic and test-locked.

## Workstream C — Interface explicitness and production-safety hardening (MEDIUM)

### C1. Remove monkey-patched runtime threshold dependency
**Goal:** Replace hidden dynamic attributes with explicit typed interface.

**Implementation tasks:**
1. Introduce explicit constructor/argument contract for runtime thresholds where needed.
2. Remove dynamic `setattr(...)` coupling.
3. Add tests validating dependency injection and backward-compatible behavior.

**Success checks:**
- No module depends on undeclared runtime-injected attributes.
- Interface contract is explicit and validated by type-aware tests.

### C2. Prevent accidental `model_stub` use in integration/live modes
**Goal:** Avoid false confidence from stub detections in Phase 2 integration.

**Implementation tasks:**
1. Require explicit predictor injection (or fail closed) for non-test integration/live execution.
2. Add guard tests that reject implicit stub usage outside test mode.
3. Add clear deterministic error message for blocked startup.

**Success checks:**
- Integration/live mode cannot run with implicit fabricated detections.
- Tests confirm deterministic hard-fail behavior.

## Suggested execution order

1. A1 (bench/live parity)
2. A2 (startup hard gate)
3. B1 (live timebase)
4. B2 (ingest channel contract)
5. C1 (explicit runtime interface)
6. C2 (stub safety hardening)
7. Full validation + sign-off evidence bundle

## How to check success for completed tasks

Use this evidence ladder for each completed task:

1. **Task test(s) green**
   - Add/update deterministic tests in `tests/test_phase2_task*.py` (or adjacent module tests) tied to the specific task acceptance condition.

2. **Boundary test(s) green**
   - Include equality and just-over-boundary cases to prove guard semantics (`<=`, `>`, `>=`) are intentional and stable.

3. **Contract test(s) green**
   - Assert explicit schema/field presence and deterministic error text for invalid inputs.

4. **Reliability/integration gates green**
   - Re-run phase2 reliability and integration-oriented suites after each workstream to ensure no regressions.

5. **Artifact/log proof captured**
   - Keep terminal logs from each executed command and preserve any required bench traces.

## Recommended command set for closure verification

Run in order and require green before sign-off:

1. `pytest tests/test_phase2_task*.py`
2. `pytest tests/test_phase2_reliability_gate.py tests/test_phase2_lane_segmentation_robustness.py`
3. `pytest tests/`
4. `pytest bench/`
5. `run_tests.bat` (firmware unit tests; run in compatible environment)
6. `pytest --cov=src/coloursorter --cov-report=xml`

## Sign-off criteria for Phase 2 completion

Phase 2 can be considered complete only when:

- All phase2 task and reliability checks are green.
- High/medium integration findings above are closed with tests.
- Bench/live behavior is parity-verified for thresholds and fault context.
- Startup diagnostics are enforced as a run gate.
- Coverage artifact (`coverage.xml`) is generated for closure run.
