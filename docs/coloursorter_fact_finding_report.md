# ColourSorter Project Fact-Finding Report

Date: 2026-03-01
Scope: repository state audit (implementation, tests, docs, readiness artifacts)

## SECTION 1 — Implementation Status

1. **Modules that currently exist and are functional**
   - **CV / pipeline:** `preprocess`, `calibration`, `eval`, `deploy` are present and covered by unit/integration tests.
   - **Serial / protocol path:** `serial_interface`, `protocol`, and bench `serial_transport` are present and tested.
   - **Scheduler:** present in `src/coloursorter/scheduler/output.py` with validation and tests.
   - **GUI:** PySide6 bench GUI exists in `gui/bench_app` with controller tests.
   - **MCU code:** **UNKNOWN in this repo** (no firmware source tree/versioned MCU implementation found).

2. **Modules never tested end-to-end**
   - End-to-end path with a **real MCU firmware implementation** is not testable from this repository alone (firmware absent here).
   - GUI + serial + real hardware interaction is not covered by automated in-repo tests as a full E2E chain.
   - In-repo E2E coverage is bench-centric (mock transport plus integration tests), not full physical-stack E2E.

3. **Known runtime errors or freezes**
   - No failing tests were observed in the current test run (`pytest -q` passed).
   - No explicit hard freeze defect is recorded as failing CI evidence in-repo.
   - **Risk noted:** GUI cycle work performs detection/transport work in timer-driven controller flow; serial read latency/timeout can still affect responsiveness depending on runtime serial timeout settings.

---

## SECTION 2 — Build System

4. **Current build system**
   - Python packaging via **`pyproject.toml` + setuptools** (`setuptools.build_meta`).
   - Not CMake/qmake; this is a Python project (with Qt via PySide6).

5. **Languages by layer**
   - Host pipeline / bench / protocol / scheduler / config / tests: **Python**.
   - GUI: **Python (PySide6/Qt)**.
   - MCU firmware language: **UNKNOWN in this repo**.

6. **Required Qt version**
   - Dependency specifies **PySide6 `>=6.6,<7.0`**.

7. **External dependencies (declared)**
   - Runtime:
     - `PySide6>=6.6,<7.0`
     - `opencv-python>=4.9,<5.0`
   - Optional test:
     - `pytest>=8.0,<9.0`
     - `pytest-cov>=5.0,<6.0`
   - Optional lint:
     - `ruff>=0.6,<0.7`
   - Runtime note: serial transport requires `pyserial` when serial mode is used (loaded dynamically).

---

## SECTION 3 — Execution & Threading

8. **Single-threaded vs threaded/asynchronous**
   - No explicit worker thread pools/`QThread`/`asyncio` runtime orchestration were identified for core bench GUI flow.
   - GUI/controller work is event-loop driven (`QStateMachine`, `QTimer`, signals/slots) and effectively single-threaded in normal flow.

9. **Is GUI currently blocking on long-running operations?**
   - Potentially yes: detection and transport command/response actions are executed during controller cycle ticks; if serial operations or frame/detection processing are slow, GUI responsiveness risk exists.

10. **Are serial and CV operations safe for a GUI thread?**
   - Functionally implemented and tested for bench-level behavior.
   - Architecturally, they are not isolated in dedicated workers in this repo; so safety for responsiveness depends on operation latency and timeout configuration.

---

## SECTION 4 — MCU & Hardware Status

11. **MCU(s) currently used**
   - **UNKNOWN in repository source.**
   - Repository contains hardware-readiness evidence logs and protocol traces, but not a versioned firmware codebase identifying specific MCU platform.

12. **Firmware features (SAFE mode, homing, encoder) tested/stable?**
   - SAFE/watchdog behavior has passing readiness evidence and report status.
   - Homing/encoder logic is represented in host bench/runtime config and virtual encoder tests.
   - Firmware-internal implementation stability is **not directly auditable here** due to missing firmware source.

13. **Queueing system functional?**
   - Yes for bench/protocol surfaces: queue semantics have tests and readiness artifacts; strict hardware-readiness report currently passes queue criterion.

14. **Servo actuations observable and repeatable?**
   - **UNKNOWN from repository code/tests.**
   - Bench command scheduling and protocol traces exist, but physical actuator repeatability evidence is not explicitly captured as servo metrology data in this repo.

---

## SECTION 5 — Documentation & Spec

15. **Spec documents present**
   - OpenSpec index and mirror (`openspec.md`, `docs/openspec/README.md`, `docs/openspec/v3/*`).
   - Agent guidance (`agents.md`).
   - ICD (`docs/openspec/icd.md`).
   - State machine (`docs/openspec/v3/state_machine.md`).
   - Timing budget (`docs/openspec/v3/timing_budget.md`) plus readiness timing artifacts.
   - Protocol/data/config/contracts mirrors and compliance matrices are present.

16. **Completeness/accuracy relative to implementation**
   - Generally strong and intentionally mirrored against runtime files.
   - Test suite includes OpenSpec artifact parity/compliance checks.
   - Some documented risk remains around policy/behavior drift areas (notably SAFE/mode semantics and bench-vs-hardware interpretation edges).

17. **Known drift issues (examples)**
   - SAFE policy surface divergence risk between host transition constraints and GUI recovery behavior.
   - Bench-vs-hardware parity limits where firmware behavior is external to this repo.
   - Historical stale path references noted in prior engineering audit for sprint/task docs.

---

## SECTION 6 — Project Goals & Priorities

18. **Primary objective of next milestone (inferred from repo governance/audit artifacts)**
   - Close high-risk bench↔hardware parity gaps and preserve OpenSpec v3 protocol/state consistency while maintaining deterministic bench validation.

19. **Secondary objectives**
   - Improve GUI/transport observability and responsiveness safeguards.
   - Tighten protocol semantic alignment (ACK/NACK/mode transitions).
   - Keep artifact and path references synchronized with current package layout.

20. **POC constraints to respect**
   - Timing budget conformance and deterministic telemetry.
   - Architecture consistency with OpenSpec v3 contracts and runtime mirrors.
   - GUI responsiveness (avoid long-running synchronous work on UI loop).
   - Minimal hardware risk via SAFE/watchdog-compliant flows and queue backpressure handling.

---

## SECTION 7 — Summary Table

| Area | Status | Known Issues | Comments |
| ---- | ------ | ------------ | -------- |
| CV/pipeline (`preprocess`, `calibration`, `deploy`, `eval`) | Implemented + tested | Detection provider maturity is baseline/simple | Bench-first flow is solid; hardware signal quality still external. |
| Scheduler | Implemented + tested | None critical found in current tests | Validation/range guards in place. |
| Serial/protocol host | Implemented + tested | Semantics drift risk at policy edges (SAFE/NACK interpretation) | Bench and protocol compliance artifacts exist. |
| Bench runtime | Implemented + tested | Bench-centric confidence higher than hardware E2E confidence | Mock + serial transport paths exist. |
| GUI bench app | Implemented + tested | Potential responsiveness risk under slow CV/serial operations | Event-loop/timer design; no dedicated worker threading in core path. |
| MCU firmware | UNKNOWN in repo | Firmware source/platform not versioned here | Hardware evidence logs exist, but implementation not auditable from code. |
| Queue behavior | PASS in readiness report | Hardware parity still depends on external firmware/runtime | Strict readiness gate currently passes. |
| SAFE/watchdog | PASS in readiness report | Transition policy consistency must stay aligned across layers | Recovery evidence exists for bench + hardware artifacts. |
| Documentation/OpenSpec artifacts | Comprehensive and mirrored | Drift can occur when code and policy evolve | Matrices, ICD, state machine, timing budget, contracts all present. |
| Overall readiness | Bench-ready; partial hardware certainty | No in-repo firmware + limited physical E2E observability | Good foundation for next POC integration hardening. |
