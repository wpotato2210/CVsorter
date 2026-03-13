# Phase 3 Start Assessment (Action-Oriented)

## 1) Current State Summary

### Complete
- Deterministic host-side protocol framing/parsing and v3 ACK/NACK token handling are implemented and heavily covered by tests.
- Bench stack is operational (replay/live sources, scenarios, evaluation artifacts, serial/mock transports) with green end-to-end host test suite.
- Phase-3 safe-now scaffolding tasks T3-001..T3-004 exist (fixtures, deterministic harness tests, informational HIL gate tooling).
- Firmware core safety/queue/scheduler primitives and command-dispatch skeleton exist for HELLO/HEARTBEAT/SET_MODE/SCHED/GET_STATE/RESET_QUEUE.

### Partially implemented
- Phase 3 protocol parity is only partially landed: firmware has command dispatch logic, but full runtime serial parser/framing + strict protocol conformance harness to MCU target is not complete.
- Trigger-correlation (T3-003) and HIL enforcement (T3-004) are currently informational (xfail placeholders), not release-gating.
- Bench/live parity hardening is present in tests, but prior audit flags integration gaps that still need production-hard guarantees.

### Critical missing
- Deterministic firmware UART receive/parser execution path with validated framing/CRC before command execution.
- Deterministic actuator dispatch loop from queued events to hardware pulse execution with bounded jitter evidence.
- End-to-end trigger verification closure (accepted command -> terminal execution status) surfaced in host-visible telemetry and strict contract checks.
- Explicit host/MCU timebase conversion contract enforcement for trigger timestamps under jitter.

## 2) Top 5 Phase-3 Tasks

1. **Firmware protocol executor completion (3.1 closeout)**
   - Purpose: Move from host-emulated protocol confidence to actual MCU protocol determinism.
   - Impact: Unlocks real hardware confidence and prevents protocol drift between Python and firmware paths.
   - Complexity: High.
   - Likely files/modules:
     - `firmware/mcu/src/main.c`, `firmware/mcu/src/command_dispatch.c`, `firmware/mcu/src/isr.c`
     - `firmware/mcu/include/*.h`
     - `tools/firmware_readiness_check.py`, protocol conformance tests in `tests/`.

2. **Deterministic actuator dispatcher on MCU (3.2)**
   - Purpose: Convert scheduled queue items into bounded, safe, deterministic actuation.
   - Impact: Enables real reject pulses and production-like behavior validation.
   - Complexity: High.
   - Likely files/modules:
     - `firmware/mcu/src/scheduler.c`, `firmware/mcu/src/main.c`, safety/watchdog interfaces
     - new/extended firmware actuator driver files under `firmware/mcu/src/` and `firmware/mcu/include/`
     - timing tests in `tests/` and bench fixtures.

3. **Trigger verification reconciliation (3.3)**
   - Purpose: Guarantee terminal status for each accepted schedule command.
   - Impact: Closes see->decide->trigger->verify loop; critical for production trust and incident debugging.
   - Complexity: Medium-High.
   - Likely files/modules:
     - `src/coloursorter/serial_interface/serial_interface.py`
     - `src/coloursorter/bench/serial_transport.py`, `src/coloursorter/bench/evaluation.py`
     - `tests/test_phase3_t3_003_trigger_correlation_design.py` (promote from placeholder to gating).

4. **Timebase contract unification and jitter envelope enforcement (3.4)**
   - Purpose: Make host scheduling and MCU execution comparable in one deterministic timing model.
   - Impact: Prevents latent field timing misses and false confidence from synthetic timing assumptions.
   - Complexity: Medium.
   - Likely files/modules:
     - `src/coloursorter/bench/runner.py`, `src/coloursorter/runtime/live_runner.py`
     - scheduler/timing evaluation tests and fixtures in `tests/fixtures/timing_jitter_t3_002.json`
     - timing artifact scripts under `tools/`.

5. **Promote informational HIL gate to release-blocking deterministic gate (3.6)**
   - Purpose: Enforce repeated-run determinism and hardware parity in CI/release flow.
   - Impact: Converts quality evidence from “best effort” to merge/release criterion.
   - Complexity: Medium.
   - Likely files/modules:
     - `tools/hil_informational_gate.py` -> hardened gate tool
     - `tests/test_phase3_t3_004_hil_gate.py` (remove placeholder behavior)
     - CI/workflow integration + readiness check tooling.

## 3) Immediate Next Task (Implement First)

### Highest-signal first task
- **Task:** Finish Phase 3.1 firmware protocol executor parity with deterministic conformance vectors against MCU path.

### Why first
- It is a hard dependency for 3.2/3.3/3.4; without protocol-exact MCU command handling, downstream timing and trigger-verification work cannot be trusted.
- It directly addresses the roadmap’s first release-blocking gap.

### Implementation plan (small, testable increments)
1. Add/complete UART frame ingestion + deterministic parser in firmware (strict tokenization, bounded buffers, explicit invalid-frame outcomes).
2. Route parsed commands through `fw_dispatch_command` and serialize canonical ACK/NACK response frames.
3. Add fixed protocol vector replay harness that runs the same command packs currently used on host path against firmware target/emulation.
4. Add deterministic rerun checks: same vectors must yield byte-identical responses across runs.
5. Wire into readiness tooling so parity failures are surfaced as explicit gate failures.

### File-level change suggestions
- Firmware core:
  - `firmware/mcu/src/main.c` (event loop integration for receive->dispatch->respond)
  - `firmware/mcu/src/isr.c` (UART RX buffering boundaries)
  - `firmware/mcu/src/command_dispatch.c` + related headers for canonical response mapping
- Host/tooling/tests:
  - `tools/firmware_readiness_check.py`
  - add/update tests under `tests/test_firmware_protocol_parity_gate.py` and protocol-vector coverage tests.

## 4) Risk Assessment

### Architectural risks
- Bench/live/firmware behavior drift if protocol authority remains split across paths.
- Implicit runtime contracts (dynamic attributes, loose ingest assumptions) reduce long-term maintainability and parity confidence.

### Performance risks
- Trigger timing confidence can be overstated if live capture timing remains synthetic or if host/MCU timebase conversion is not explicit.
- Queue/dispatch behavior under load may violate jitter bounds without deterministic dequeue/actuation instrumentation.

### Technical debt likely to slow Phase 3
- Informational-only placeholders for T3-003/T3-004 delay transition to hard release evidence.
- Existing integration audit findings indicate unresolved parity and startup-gating issues that may cause rework during firmware integration.
