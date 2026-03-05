# Deep Autonomous Repository Audit (Ultra Mode)

## 1. Project Overview

### Purpose
ColourSorter is a deterministic computer-vision bench and runtime system for lane-based reject/accept decisions, command scheduling, and MCU protocol validation.

### Intended users
- Bench operators running replay/live validation.
- Developers extending CV, transport, and GUI modules.
- Firmware/protocol engineers validating host↔MCU interoperability.

### Technology stack
- **Languages:** Python, C (firmware).
- **Core Python deps:** PySide6, OpenCV, PyYAML.
- **Optional deps:** pyserial for hardware transport.
- **Packaging:** setuptools + console scripts.

### External services/interfaces
- Local camera device via OpenCV.
- Serial/ESP32-connected MCU transport.
- Filesystem-based artifact/config/contract inputs.

---

## 2. Architecture Map

### Layer model (observed)
1. **Contracts/configs**: `contracts/`, `protocol/`, `configs/`.
2. **Core CV decisioning**: preprocess → calibration → eval → scheduler.
3. **Transport/protocol**: framing/ACK-NACK parsing and serial transport.
4. **Execution surfaces**: bench CLI, scenario CLI, live runtime, GUI app.
5. **Firmware counterpart**: MCU command dispatch/scheduler/watchdog stubs.

### Major components
- `deploy/pipeline.py`: deterministic decision + scheduling orchestration.
- `deploy/detection.py`: provider implementations (`opencv_basic`, `opencv_calibrated`, `model_stub`).
- `bench/runner.py`: cycle orchestration, telemetry, safety/fault policies.
- `serial_interface/serial_interface.py`: framing, CRC, ACK/NACK parsing.
- `bench/serial_transport.py`: handshake/heartbeat/retry/state sync transport logic.
- `config/runtime.py`: custom YAML-like parsing + strict config validation.
- `gui/bench_app/controller.py`: operator state machine and control surface wiring.
- `firmware/mcu/src/*.c`: host command handling and runtime state transitions.

---

## 3. Execution Flow

### Bench replay/live CLI (`coloursorter.bench.cli:main`)
1. Parse args and optional runtime config.
2. Build scenarios, pipeline, transport, encoder, and safety budgets.
3. Open frame source (replay/live), detect objects, run pipeline.
4. Process ingest payload via `BenchRunner` and transport send loop.
5. Evaluate scenario results and write artifacts.

### Scenario evaluator CLI (`coloursorter.bench.scenario_runner:run`)
1. Parse RTT and safety transition args.
2. Evaluate static scenarios only.
3. Emit pass/fail with process exit code.

### Live runtime (`runtime/live_runner.py`)
1. Load runtime config and reject profiles.
2. Build live detector + transport + pipeline.
3. Capture frames, detect, pipeline-run, send scheduled commands.
4. Emit optional per-cycle reports; enforce periodic cycle timing.

### Protocol flow
`ScheduledCommand` → wire encode with CRC → serial write/readline → parse frame + parse ACK/NACK → map to `TransportResponse` and fault state.

---

## 4. File-Level Findings

### `src/coloursorter/deploy/pipeline.py`
- Clear deterministic structure and calibration/lane hot-reload behavior.
- Risk: mtime-based reload without synchronization may race in multithreaded callers.

### `src/coloursorter/preprocess/lane_segmentation.py`
- Uses regex + `ast.literal_eval` parser for lane geometry text.
- Risk: bespoke YAML parsing is brittle; easy to misparse valid YAML variants.

### `src/coloursorter/config/runtime.py`
- Extensive validation and typed config dataclasses.
- Risk: custom `_parse_simple_yaml` supports only a YAML subset and may diverge from documented YAML expectations.
- Risk: imports `importlib.util` but parser doesn’t use a hardened YAML library despite depending on PyYAML.

### `src/coloursorter/bench/cli.py`
- Comprehensive bench execution wiring with artifacts and audit trail.
- Risk: `_build_detector` uses `next(...)` without fallback, raising uncaught `StopIteration` for missing recipe pair.

### `src/coloursorter/bench/runner.py`
- Rich safety instrumentation and telemetry emission.
- Risk: artificial response via dynamic `type("_Resp", ...)` objects reduces type safety and can hide schema drift.

### `src/coloursorter/bench/serial_transport.py`
- Good retry/heartbeat/handshake mechanics and fault-state mapping.
- Risk: no explicit correlation check between sent `msg_id` and response `msg_id`; stale/reordered ACKs could be accepted.

### `src/coloursorter/serial_interface/serial_interface.py`
- Strong framing and CRC enforcement, token length bounds, ACK/NACK schema checks.
- Risk: queue depth upper bound is not validated against configured max depth.

### `src/coloursorter/ingest/adapter.py`
- Defensive payload type/range checks and monotonic timestamp handling.
- Risk: contract file currently mirrors wire-frame schema, forcing hardcoded ingest-required keys and reducing contract authority.

### `gui/bench_app/controller.py`
- Broad orchestrator with GUI state machine, transport, runtime thresholds, queue controls.
- Risk: very large controller class implies high coupling and reduced testability.

### `firmware/mcu/src/main.c`
- Minimal loop initializes watchdog/brownout/scheduler and kicks watchdog forever.
- Risk: no command ingestion loop yet; current behavior appears scaffold-level rather than production firmware.

---

## 5. Static Code Review Issues

1. **Uncaught recipe lookup failure**
   - **Location:** `src/coloursorter/bench/cli.py` (`_build_detector`).
   - **Issue:** `next(...)` on profile match can raise `StopIteration`.
   - **Risk:** runtime crash with poor operator error context.
   - **Remediation:** use explicit search helper and raise `ValueError` with available recipes.

2. **Protocol response correlation gap**
   - **Location:** `src/coloursorter/bench/serial_transport.py` (`_send_frame`).
   - **Issue:** parsed response not checked against reserved `msg_id`.
   - **Risk:** stale/duplicate/reordered responses can be treated as current ACK.
   - **Remediation:** compare parsed `msg_id` to expected, retry or enter safe state on mismatch.

3. **Brittle ad-hoc YAML parser**
   - **Location:** `src/coloursorter/config/runtime.py` (`_parse_simple_yaml`).
   - **Issue:** limited parser semantics and custom indentation/list handling.
   - **Risk:** config incompatibility and subtle parsing discrepancies.
   - **Remediation:** replace with `yaml.safe_load` + existing validation checks.

4. **Hot-reload thread safety not enforced**
   - **Location:** `src/coloursorter/deploy/pipeline.py`.
   - **Issue:** mutable runner state (`_geometry`, `_calibration`) updated without lock.
   - **Risk:** inconsistent reads in concurrent use.
   - **Remediation:** add lock around reload + run critical path or document single-thread contract.

5. **Type-erased synthetic responses**
   - **Location:** `src/coloursorter/bench/runner.py`.
   - **Issue:** dynamic anonymous objects mimic transport response fields.
   - **Risk:** silent runtime attr drift and weaker static reasoning.
   - **Remediation:** use a concrete dataclass (e.g., `TransportResponse`) for all branches.

6. **Config-contract mismatch workaround**
   - **Location:** `src/coloursorter/ingest/adapter.py` + `contracts/frame_schema.json`.
   - **Issue:** ingest adapter bypasses contract authority due to incompatible schema file.
   - **Risk:** drift between intended ingest schema and enforced validation.
   - **Remediation:** create dedicated ingest schema and validate against it directly.

7. **Controller cohesion/size issue**
   - **Location:** `gui/bench_app/controller.py`.
   - **Issue:** single class owns transport, UI, state machine, queueing, logging, runtime policy.
   - **Risk:** regression-prone changes and low unit-test isolation.
   - **Remediation:** split into UI adapter, runtime coordinator, and transport/session manager.

8. **Firmware runtime loop incomplete**
   - **Location:** `firmware/mcu/src/main.c`.
   - **Issue:** no active command read/dispatch loop after startup HELLO.
   - **Risk:** bench assumptions won’t hold on actual target runtime.
   - **Remediation:** implement deterministic receive/dispatch/tick loop with watchdog-safe timing.

---

## 6. Security Audit Results

### Secrets & credentials
- No obvious hardcoded API keys/tokens/passwords were found in source/config scan.
- Remaining concern: no centralized secret-management guidance for deployment hardening.

### Input safety
- **Positive:** robust serial frame validation (CRC, framing, token constraints).
- **Gap:** transport layer does not bind response `msg_id` to request, enabling potential replay/misassociation issues on noisy links.

### Authentication/authorization
- Protocol model appears trust-on-link with no cryptographic auth.
- `security_model.md` explicitly leaves auth model as open question.

### Configuration safety
- Strong bounds checking in runtime config model.
- Custom parser increases risk of malformed-but-accepted config variants.

### Dependency risks
- Runtime uses broad major-range pins (e.g., OpenCV `<5.0`, PySide6 `<7.0`), which can still permit ABI/behavior drift in minor updates.
- Firmware toolchain lock exists (good), but Python lockfile strategy is absent.

### Severity ratings
- **High:** msg_id correlation gap in serial transport.
- **Medium:** custom YAML parser fragility.
- **Medium:** missing explicit authn/authz model for command producers.
- **Low:** no formal secret-management/deployment hardening runbook.

---

## 7. Architecture Evaluation

### Strengths
- Clear domain decomposition across preprocess/eval/scheduler/transport.
- Strong use of dataclasses and explicit boundary validation.
- Protocol constants centralized and reused across modules/tests.
- Safety/fault telemetry integrated into bench runner.

### Weaknesses
- Execution surface fragmentation (`scenario_runner` vs full bench CLI) creates user confusion.
- GUI controller is monolithic and highly coupled.
- Contract layer blurred by ingest-vs-wire schema reuse.
- Thread-safety and concurrency boundaries are not explicit in pipeline/transport usage docs.

---

## 8. Documentation Review

### Present and useful
- README/Quick Start with beginner-focused install/run steps.
- Developer guide with package/component map.
- Architecture/security/deployment model docs and OpenSpec set.

### Missing/unclear
1. **CLI surface clarity gap:** package script maps `coloursorter-bench-cli` to scenario evaluator, while full pipeline CLI is `python -m coloursorter.bench.cli`; docs mention both but not as a formal split contract.
2. **Production deployment runbook incompleteness:** deployment doc lists open questions on platform matrix and promotion gates.
3. **Security model unresolved areas:** auth model and malformed-frame handling policy are explicitly undecided.
4. **Schema governance ambiguity:** ingest contract expectations are not represented by a dedicated schema file.

---

## 9. Technical Debt Inventory

### Quick Wins (low effort / high impact)
1. Add explicit recipe-resolution error handling in bench CLI.
   - Impact: operator-facing reliability.
   - Effort: Low.
   - Dependency: none.
2. Validate response/request `msg_id` match in serial transport.
   - Impact: protocol correctness + safety.
   - Effort: Low.
   - Dependency: transport tests updates.
3. Replace dynamic fake response objects with typed dataclass instances.
   - Impact: maintainability/testability.
   - Effort: Low.
   - Dependency: bench runner tests.

### Medium Improvements
1. Introduce dedicated ingest JSON schema and contract validator path.
   - Impact: correctness and contract governance.
   - Effort: Medium.
   - Dependency: tests + docs update.
2. Refactor GUI controller into smaller services.
   - Impact: maintainability and defect isolation.
   - Effort: Medium.
   - Dependency: signal wiring and integration tests.
3. Harmonize CLI command surface and docs.
   - Impact: developer/operator productivity.
   - Effort: Medium.
   - Dependency: entrypoint decision in `pyproject.toml`.

### Major Refactors
1. Replace custom runtime YAML parser with standard safe YAML parser + strict schema validation.
   - Impact: config reliability/security posture.
   - Effort: High.
   - Dependency: parser migration tests.
2. Formalize host runtime concurrency model with locks or single-thread executor guarantees.
   - Impact: correctness under scaling.
   - Effort: High.
   - Dependency: architecture and performance validation.
3. Implement full firmware command ingestion loop aligned with host protocol lifecycle.
   - Impact: production readiness.
   - Effort: High.
   - Dependency: MCU integration test bench.

---

## 10. Risk Prioritization Table (Top 10)

| Rank | Issue | Category | Impact | Effort |
|---|---|---|---|---|
| 1 | Missing serial response `msg_id` correlation | Security/Reliability | High | Low |
| 2 | Custom YAML parser fragility | Reliability/Maintainability | High | High |
| 3 | Uncaught detection profile lookup failure | Reliability | Medium-High | Low |
| 4 | Ingest schema mismatch and workaround | Correctness/Architecture | Medium-High | Medium |
| 5 | Monolithic GUI controller | Maintainability/Productivity | Medium | Medium |
| 6 | Thread-safety assumptions undocumented/unenforced in pipeline reload | Reliability | Medium | Medium |
| 7 | Firmware main loop lacks runtime command handling | Reliability/Readiness | Medium | High |
| 8 | CLI surface ambiguity (`scenario_runner` vs pipeline CLI) | DX/Operations | Medium | Medium |
| 9 | Missing concrete auth model for command producers | Security | Medium | High |
| 10 | Broad dependency ranges without lockfile process | Supply-chain/ops | Low-Medium | Medium |

---

## 11. Engineering Task Backlog (Implementation-Ready)

### Task 1: Enforce protocol response correlation in serial transport
- **Problem:** ACK/NACK frames are accepted without verifying `msg_id` correspondence.
- **Location:** `src/coloursorter/bench/serial_transport.py`.
- **Proposed Solution:** compare parsed `msg_id` against reserved request ID; retry on mismatch, escalate to SAFE after retry budget.
- **Acceptance Criteria:**
  - mismatched `msg_id` triggers retry behavior;
  - no response accepted if correlation fails across retries;
  - tests cover stale/reordered response scenarios.
- **Complexity:** Medium.

### Task 2: Make detection profile selection failure explicit
- **Problem:** missing camera+lighting profile can throw `StopIteration`.
- **Location:** `src/coloursorter/bench/cli.py`.
- **Proposed Solution:** helper that returns optional profile, raise `ValueError` listing available recipe pairs.
- **Acceptance Criteria:**
  - invalid recipe exits with deterministic message;
  - tests assert exact exception type and message content.
- **Complexity:** Low.

### Task 3: Introduce dedicated ingest schema
- **Problem:** ingest adapter relies on wire frame schema path and hardcoded required keys.
- **Location:** `contracts/` + `src/coloursorter/ingest/adapter.py`.
- **Proposed Solution:** add `contracts/ingest_frame_schema.json`; validate payload against it and remove workaround code.
- **Acceptance Criteria:**
  - ingest validation fails/passes per dedicated schema;
  - tests validate required keys/types/ranges against schema path.
- **Complexity:** Medium.

### Task 4: Replace ad-hoc runtime YAML parsing
- **Problem:** `_parse_simple_yaml` only partially implements YAML semantics.
- **Location:** `src/coloursorter/config/runtime.py`.
- **Proposed Solution:** use `yaml.safe_load` and keep existing field/range validation.
- **Acceptance Criteria:**
  - parser handles standard YAML examples currently documented;
  - invalid YAML yields deterministic `ConfigValidationError` wrappers;
  - regression tests cover old/new edge cases.
- **Complexity:** High.

### Task 5: Type all synthetic transport responses
- **Problem:** dynamic anonymous objects used for fallback branches.
- **Location:** `src/coloursorter/bench/runner.py`.
- **Proposed Solution:** instantiate canonical `TransportResponse` or dedicated fallback dataclass.
- **Acceptance Criteria:**
  - no use of dynamic `type("_Resp", ...)` remains;
  - static typing and tests validate branch parity.
- **Complexity:** Low.

### Task 6: Refactor GUI controller by responsibilities
- **Problem:** one large controller contains multiple domains.
- **Location:** `gui/bench_app/controller.py`.
- **Proposed Solution:** split into transport manager, runtime cycle coordinator, and UI presenter/controller shell.
- **Acceptance Criteria:**
  - each component has focused unit tests;
  - public signal behavior remains backward-compatible.
- **Complexity:** High.

### Task 7: Clarify CLI packaging contract
- **Problem:** confusion between scenario-only and full bench CLI entry points.
- **Location:** `pyproject.toml`, README, QUICK_START, DEVELOPER_GUIDE.
- **Proposed Solution:** either add distinct scripts for both paths or repoint existing script with explicit naming.
- **Acceptance Criteria:**
  - docs and scripts align 1:1;
  - smoke tests for both command surfaces pass.
- **Complexity:** Medium.

### Task 8: Add concurrency contract for pipeline reload
- **Problem:** current mutable state updates lack explicit thread guarantees.
- **Location:** `src/coloursorter/deploy/pipeline.py` + architecture docs.
- **Proposed Solution:** document single-thread requirement or add locking and thread-safety tests.
- **Acceptance Criteria:**
  - concurrency contract documented;
  - stress test validates deterministic behavior under concurrent calls (if supported).
- **Complexity:** Medium.

### Task 9: Define command-producer authentication policy
- **Problem:** security model leaves authn/authz unresolved.
- **Location:** `security_model.md`, protocol and deployment docs.
- **Proposed Solution:** decide trust model (physical-link trust vs shared secret vs signed commands) and codify enforcement.
- **Acceptance Criteria:**
  - documented threat model and chosen control;
  - implementation plan and validation checklist included.
- **Complexity:** High.

### Task 10: Implement firmware command ingestion loop
- **Problem:** MCU main currently lacks continuous command handling path.
- **Location:** `firmware/mcu/src/main.c` and dispatch/scheduler modules.
- **Proposed Solution:** add UART receive+parse+dispatch loop, scheduler tick, and watchdog-safe timeout handling.
- **Acceptance Criteria:**
  - firmware responds to HELLO/HEARTBEAT/SCHED/GET_STATE/RESET_QUEUE in loop;
  - integration logs demonstrate queue/state transitions.
- **Complexity:** High.

---

## 12. Strategic Recommendations

1. **Architecture:** adopt explicit boundary contracts per layer (ingest schema, transport schema, telemetry schema) and enforce via CI.
2. **Security:** prioritize protocol correlation hardening and finalize command authentication trust model.
3. **Testing:** expand failure-injection tests for serial ordering/replay/malformed bursts and config parsing equivalence.
4. **Reliability:** unify runtime safety semantics across bench, live runner, and GUI; avoid branch-specific response object variants.
5. **Developer workflow:** streamline CLI entrypoints, publish a “which command for which purpose” matrix, and add a lockfile/pinning strategy for reproducible environments.
