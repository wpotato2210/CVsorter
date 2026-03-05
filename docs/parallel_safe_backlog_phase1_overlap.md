# Parallel-Safe Backlog While Phase 1 Closes

## Objective
Provide parallel work that does not destabilize Phase 1 closure criteria while phase-one blockers are being resolved.

## Guardrails (Must Not Change During Overlap Window)
1. Do not modify runtime behavior tied to Phase 1 acceptance criteria for replay setup time, calibration reliability, decision/schedule payload validity, artifact completeness, provider-override reliability, or transport-path parity.
2. Keep all overlap tasks either:
   - documentation/planning-only, or
   - non-gating test/harness scaffolding behind explicit opt-in invocation.
3. No schema contract changes in overlap branch unless explicitly split into a separate post-Phase-1 deliverable.

## Parallel-Safe Task Queue

| ID | Task | Scope | Owner | Depends On | Output | Safety classification |
|---|---|---|---|---|---|---|
| OVL-001 | Normalize stale task paths and commands | Sprint tracker + phase docs | Tech Lead | None | Updated task definitions with `src/coloursorter/...` and executable checkpoints | Safe now (docs-only) |
| OVL-002 | Repair truncated task payload references | Sprint payload artifact(s) | QA/Release | OVL-001 | Machine-executable task payload with complete commands | Safe now (docs-only) |
| OVL-003 | Draft single-source state authority decision note | `mode`/`queue_depth`/`scheduler_state` ownership design note | Systems | None | Architecture decision record (ADR-style) with migration notes | Safe now (design-only) |
| OVL-004 | Prepare deterministic protocol conformance vectors for firmware target | New reusable vector files + harness invocation docs | Protocol | None | Canonical command/ACK vector pack for Phase 3.1 validation | Safe now (non-gating harness prep) |
| OVL-005 | Prepare timing-jitter replay corpus and expected envelopes | Timing harness fixtures and expected-window docs | Runtime | None | Fixed-seed jitter corpus for Phase 3.4 conformance testing | Safe now (non-gating harness prep) |
| OVL-006 | Create trigger-correlation test design package | Correlation ID, terminal status mapping test plan | Firmware+Host | OVL-004 | Test design for 1:1 command-to-terminal-status verification | Safe now (design + tests not wired to release gate) |
| OVL-007 | HIL gate scaffold (informational mode only) | `tests/` + `tools/` planning and placeholder CI job | QA Automation | OVL-004, OVL-005 | Informational deterministic HIL gate skeleton | Safe now (non-blocking by policy) |

## Deferred Until Phase 1 Closure (Do Not Start Yet)

| ID | Deferred task | Reason deferred |
|---|---|---|
| DEF-001 | Any change to replay/lane/calibration runtime behavior | Directly impacts open Phase 1 quantitative criteria |
| DEF-002 | Any transport semantic change affecting mock/serial parity outputs | Phase 1 parity criterion remains open and at risk |
| DEF-003 | Any contract/schema mutation for sched/MCU response in production path | Introduces acceptance-surface drift before Phase 1 sign-off |

## File-Level Must-Not-Touch List (Until Phase 1 Closure)
- `src/coloursorter/deploy/pipeline.py`
- `src/coloursorter/bench/runner.py`
- `src/coloursorter/bench/serial_transport.py`
- `src/coloursorter/runtime/live_runner.py`
- `contracts/sched_schema.json`
- `contracts/mcu_response_schema.json`

Exception: test-only fixtures or docs that do not alter runtime outputs are allowed.

## Exit from Overlap Mode
Overlap mode ends when:
1. full test suite is green,
2. Phase 1 quantitative evidence set is complete,
3. phase close decision is recorded.

At exit, promote OVL-004..OVL-007 outputs into active implementation tasks for Phase 3.
