# Overnight Deep Audit Report (Read-Only Analysis)

## Scope, method, and safety rails

This report was generated from static inspection only (no runtime mutation/testing execution), targeting:
- `src/coloursorter/protocol/`
- `src/coloursorter/bench/`
- `gui/bench_app/`
- `docs/openspec/v3/`
- `tests/`

Inspection command classes used for discovery/evidence:
- `find`, `rg`, `sed`, `cat`, `git log`, `git blame`

No package installation, migrations, or test execution were performed.

---

## Protocol parity

### Inventory snapshot

#### Main entrypoints
- Protocol runtime authority constants: `src/coloursorter/protocol/constants.py`
- Host command handler: `src/coloursorter/protocol/host.py` (`OpenSpecV3Host.handle_frame`)
- Canonical NACK detail mapping: `src/coloursorter/protocol/nack_codes.py`
- Mode policy matrix: `src/coloursorter/protocol/policy.py`
- Declared protocol authority pointer: `src/coloursorter/protocol/authority.py`
- Authoritative spec artifact: `docs/openspec/v3/protocol/commands.json`
- Protocol compliance declaration: `docs/openspec/v3/protocol_compliance_matrix.md`

#### Constants/schemas of record
- Command and mode constants: `constants.py`
- NACK canonical detail map + helper predicates: `nack_codes.py`
- Wire-level contract: `docs/openspec/v3/protocol/commands.json`
- Response schemas:
  - `contracts/mcu_response_schema.json`
  - `contracts/mcu_response_schema_strict.json`
  - mirrors under `docs/openspec/v3/contracts/`

#### Cross-module dependencies
- `OpenSpecV3Host` consumes `coloursorter.serial_interface.parse_frame/serialize_packet`.
- Bench transports (`serial_transport.py`, `mock_transport.py`) consume protocol constants and ACK/NACK canonicalization helpers.
- GUI controller consumes both protocol host fallback and mode transition policy (`is_mode_transition_allowed`).

#### Potential drift points
- Duplicate authority mirrors (`protocol/commands.json` vs `docs/openspec/v3/protocol/commands.json`).
- Duplicate response contracts (`contracts/*.json` vs `docs/openspec/v3/contracts/*.json`).
- Compliance matrix references test function names that have drifted.

### Invariant contradiction mining (protocol)

#### Invariant A — NACK semantics
- **Spec says:** NACK codes 1..8 are canonical, and code 7 is reserved for `BUSY` detail (plus matrix text explicitly calls out non-canonical handling).
- **Runtime does:**
  - Host emits canonical `(7, BUSY)` when locked/busy (`CANONICAL_NACK_7`).
  - Serial transport maps non-canonical combinations to SAFE fallback, with explicit WATCHDOG path only when `nack_code is None` and detail is `WATCHDOG`.
- **Tests enforce:**
  - canonical busy pair tests exist and non-canonical detail -> SAFE behavior is covered.
  - matrix references one outdated test function name: `...watchdog_as_safe` (actual function is `...detail_as_safe`).
- **Mismatch status:** `partial` (behavior aligned, compliance documentation test reference drifted).

#### Invariant B — SAFE transitions
- **Spec says:** `SAFE -> AUTO` is forbidden; recovery path `SAFE -> MANUAL -> AUTO`; mode authority host-owned; GUI command-driven only.
- **Runtime does:**
  - Policy matrix in `policy.py` forbids direct SAFE->AUTO.
  - Host rejects disallowed transitions with NACK 5.
  - GUI recovery routines gate by controller state and transition policy (`recover_safe_to_manual`, `recover_to_auto`).
- **Tests enforce:** mode policy and recovery tests exist in protocol and controller suites.
- **Mismatch status:** `aligned`.

#### Invariant C — queue depth truth
- **Spec says:** ACK metadata / GET_STATE are authoritative; caches are derived-only and must not trigger reset alone.
- **Runtime does:**
  - Serial transport updates cache from ACK when depth present.
  - `_sync_state_before_sched` resets only on mode/scheduler mismatch, not queue-depth mismatch.
- **Tests enforce:** explicit drift test verifies stale derived depth does not trigger `RESET_QUEUE`.
- **Mismatch status:** `aligned`.

#### Invariant D — trigger timestamps
- **Spec says:** generation anchored on latest observed pulse (or previous frame if none); projected trigger timestamp includes schedule + travel; zero-speed locks projection to generation timestamp.
- **Runtime does:**
  - `VirtualEncoder.resolve_trigger_generation_timestamp` and `project_trigger_timestamp` implement this model.
  - Bench runner uses encoder-derived generation + projection and logs fields to `BenchLogEntry`.
- **Tests enforce:** deterministic, zero-speed, and dropout cases are covered in `tests/test_determinism_and_telemetry.py`.
- **Mismatch status:** `aligned`.

---

## Transport behavior

### Runtime pathway map
- `SerialMcuTransport.send`:
  1. `_ensure_link_ready` (HELLO/HEARTBEAT/GET_STATE sync)
  2. `_send_frame(SCHED, ...)`
  3. `_map_ack_to_bench_state`
  4. cache update (`queue_depth`, `queue_cleared`) and response assembly

### Notable behaviors
- Retry/backoff on no response up to `max_retries`, then structured timeout error (`SerialTransportError`).
- Parse errors force SAFE fault and mark in-flight command uncertain.
- Heartbeat failure causes resync path and SAFE escalation where needed.
- State sync can issue `RESET_QUEUE` + `SET_MODE` to reconcile protocol/expected state.

### Drift signal
- Compliance matrix claims retry tests with specific names that are currently absent from `tests/test_serial_transport.py`.
- Runtime still includes retry/backoff code path, but explicit named coverage appears drifted in docs.

---

## GUI-state consistency

### Entry points and state authority
- Main GUI orchestration: `gui/bench_app/controller.py` (`BenchAppController`).
- GUI state machine: `BenchControllerStateMachine` (IDLE/REPLAY/LIVE/FAULTED/SAFE).
- Operator mode state managed via `_set_operator_mode`; protocol mode changes via `_set_protocol_mode`.

### Consistency findings
- Queue state emitted from transport-observed depth (derived cache), not ad hoc local increments.
- Queue clear side effects are applied only from protocol queue-cleared metadata or transport observation helper.
- SAFE home path triggers `recover_safe_to_manual` only (no forced SAFE->AUTO shortcut).
- Operator events are tagged `record_type="operator_event"`, respecting telemetry scope guidance.

### Potential weak spots
- `_send_protocol_command` may bypass physical transport when `send_command` absent and fallback host instance is used; this can diverge from real serial behavior in mixed configurations.
- GUI uses both local protocol host and transport interface depending on wiring, creating dual-path semantics risk.

---

## Telemetry semantics

### Schema intent
`docs/openspec/v3/telemetry_schema.md` defines mandatory cycle fields and limits timing invariants to `record_type=actuation_cycle`.

### Runtime realization
- `BenchLogEntry` includes required timing, queue, mode, scheduler, nack fields and extensive hardened fields.
- `BenchRunner.run_cycle` emits `actuation_cycle` logs with trigger generation/projection semantics.
- GUI-generated non-cycle entries use `operator_event`.

### Drift/ambiguity notes
- Runtime field names are suffixed (`*_s`) while spec references unsuffixed names (`frame_timestamp`, `trigger_timestamp`). Existing tests appear to accept runtime model, but terminology mismatch can confuse downstream consumers.

---

## Artifact drift

### Confirmed drift
1. **Protocol compliance matrix references stale test names** (documentation drift).
2. **Duplicate test function name in `tests/test_openspec_artifacts.py`**:
   - `test_mcu_response_schema_enforces_conditional_ack_nack_requirements` defined twice.
   - In Python module scope, latter definition overrides earlier, silently reducing asserted coverage.
3. **Multi-copy authority pattern** remains high-maintenance:
   - protocol command artifact mirrored in two places.
   - schema contracts mirrored in two trees.
   - GUI layout JSON mirrored in runtime and docs.

### Why this matters
- Governance docs can claim validation that is no longer executable under the named handles.
- Overwritten tests create false confidence while preserving green status.
- Mirror files invite latent divergence unless tooling enforces strict parity.

---

## Test-gap analysis

### Critical behavior matrix

| Behavior | Unit coverage | Integration coverage | E2E coverage | Missing assertions | Priority |
|---|---|---|---|---|---|
| ACK/NACK canonicalization | Medium (mapping helpers covered) | Medium (host + serial mapping tests) | Low | Doc-matrix ↔ actual test-name consistency checks; explicit assertion that *all* matrix-linked tests exist. | P0 |
| Mode transition constraints | Medium | Medium-High (host + GUI transition tests) | Low | E2E assertion for full SAFE recovery under real serial transport and GUI command path. | P1 |
| Queue clear and queue depth propagation | Medium | Medium-High (`GET_STATE`, reset, drift tests) | Low | Assertion that GUI queue widget reflects `queue_cleared` transitions under both serial/mock transports. | P1 |
| Telemetry timestamp semantics | High (encoder + runner deterministic tests) | Medium | Low | Contract-level assertions mapping spec names to runtime field names (or explicit alias policy test). | P1 |
| Artifact parity | Medium (presence/parity checks exist) | Low-Medium | Low | Guard against duplicate test-function names; validation that docs matrix references extant tests. | P0 |

---

## Risk register

| ID | Risk | Severity | Confidence | Blast radius | Reproducibility |
|---|---|---|---|---|---|
| R1 | Compliance matrix names tests that no longer exist | High | High | docs/tests/governance | Static |
| R2 | Duplicate pytest function name overwrites stricter schema assertions | High | High | tests/contracts/docs confidence | Static |
| R3 | Runtime/spec telemetry naming mismatch (`*_s` vs unsuffixed) | Medium | Medium | telemetry consumers/docs/tests | Static/Inferred |
| R4 | Dual command paths in GUI (`transport.send_command` vs fallback host) can diverge | Medium | Medium | GUI/protocol/transport | Inferred |
| R5 | Multi-copy artifacts increase drift probability across protocol/schema/layout | Medium | High | protocol/docs/contracts/gui/tests | Static |
| R6 | Retry policy documentation references absent concrete tests | Medium | High | transport/docs/test credibility | Static |
| R7 | NACK detail canonicalization expectations are nuanced and easy to regress without matrix-to-code contract tests | Medium | Medium | protocol/transport/tests | Inferred |
| R8 | SAFE/WATCHDOG semantics can be conflated when non-canonical NACK detail is received | Medium | Medium | transport/ops telemetry | Inferred |
| R9 | Queue depth cache may be misinterpreted by future contributors as authoritative | Medium | Medium | transport/gui | Inferred |
| R10 | Hardware validation links in docs may become stale without automated existence checks | Low-Medium | Medium | docs/release evidence | Static |

---

## Execution backlog (implementation-ready)

### Task B1 — Governance/test-link integrity checker
- **Priority:** P0
- **Effort:** S
- **Dependencies:** none
- **Acceptance criteria:**
  - Parse `docs/openspec/v3/*matrix*.md` test references.
  - Verify referenced files/functions exist.
  - CI fails on missing references.
- **Verification commands (later):**
  - `python -m pytest tests/test_openspec_artifacts.py`
  - `python tools/validate_matrix_test_links.py`

### Task B2 — Fix duplicate pytest function-name collision
- **Priority:** P0
- **Effort:** S
- **Dependencies:** none
- **Acceptance criteria:**
  - Unique test names in `tests/test_openspec_artifacts.py`.
  - Both strict and non-strict schema conditional assertions execute.
- **Verification commands (later):**
  - `python -m pytest tests/test_openspec_artifacts.py -q`

### Task B3 — Telemetry terminology harmonization
- **Priority:** P1
- **Effort:** M
- **Dependencies:** B1 optional
- **Acceptance criteria:**
  - Decide canonical field names (spec-level aliases or runtime renames).
  - Add explicit compatibility table + tests ensuring mapping is stable.
- **Verification commands (later):**
  - `python -m pytest tests/test_determinism_and_telemetry.py tests/test_bench_evaluation.py -q`

### Task B4 — GUI transport-path unification hardening
- **Priority:** P1
- **Effort:** M
- **Dependencies:** none
- **Acceptance criteria:**
  - One authoritative command dispatch path per deployment mode.
  - Added tests for parity between serial and fallback paths.
- **Verification commands (later):**
  - `python -m pytest tests/test_bench_controller.py tests/test_bench_controller_gui.py -q`

### Task B5 — Duplicate-authority reduction plan
- **Priority:** P2
- **Effort:** L
- **Dependencies:** B1
- **Acceptance criteria:**
  - Introduce generated mirrors or single-source import flow.
  - CI parity checks for protocol/schema/layout mirrors.
- **Verification commands (later):**
  - `python -m pytest tests/test_openspec_artifacts.py tests/test_protocol_static_guard.py -q`

---

## Top 10 highest-risk contradictions

1. Protocol compliance matrix cites `test_protocol_supports_all_v3_commands`, but actual test is `..._with_handshake`.
2. Matrix cites non-existent `test_serial_transport_treats_noncanonical_nack_code_7_watchdog_as_safe`.
3. Matrix cites non-existent queue-clear test handle for protocol compliance.
4. Matrix cites non-existent retry-policy test handles.
5. Duplicate test function name in artifact parity suite causes earlier stricter assertion block to be shadowed.
6. Telemetry doc canonical names differ from runtime dataclass field naming convention.
7. GUI can issue protocol commands through fallback host rather than actual transport under some paths.
8. Dual-source mirrored artifacts remain vulnerable to out-of-band edits.
9. WATCHDOG representation split (transport error semantics vs NACK details) is correct but subtle and under-documented in runtime comments.
10. Governance docs report hardware validation links without automated freshness checks.

---

## Next 3 PR bundles (dependency order + rollback notes)

### PR Bundle 1 — “Doc/Test Integrity Fast Fix”
- **Contains:** B1 + B2 + compliance matrix reference corrections.
- **Dependencies:** none.
- **Rollback:** revert markdown + small test updates only; no runtime behavior impact.

### PR Bundle 2 — “Telemetry Contract Clarification”
- **Contains:** B3 (alias table, schema/docs/runtime naming alignment tests).
- **Dependencies:** Bundle 1 recommended.
- **Rollback:** keep runtime stable; roll back docs/alias tests if downstream consumers object.

### PR Bundle 3 — “Transport/GUI Authority Consolidation”
- **Contains:** B4 + initial B5 scaffolding (parity checks/generation tooling).
- **Dependencies:** Bundle 1 complete; Bundle 2 optional.
- **Rollback:** feature-flag fallback path; retain previous dispatch behavior while disabling new strict checks.

---

## Human decisions required (explicit blockers)

1. **Telemetry naming authority:** keep runtime `*_s` names and document aliases, or rename runtime fields to spec names.
2. **Single source strategy:** choose whether docs or runtime contracts are primary source for generated mirrors.
3. **GUI command path policy:** should fallback host dispatch remain for offline tooling, or be prohibited in production profile.
4. **WATCHDOG semantics policy:** keep current split (timeout telemetry vs NACK code detail constraints) or formalize additional wire-level code/detail combinations.
5. **Governance strictness:** enforce “doc references must resolve to executable test handles” as a release gate.

---

## Appendix A — Subsystem inventory and drift hotspots

### `src/coloursorter/protocol/`
- Entrypoints: `host.py`, `constants.py`, `nack_codes.py`, `policy.py`.
- Drift hotspots: duplicated command constants vs JSON authority; NACK mapping assumptions consumed by multiple transports.

### `src/coloursorter/bench/`
- Entrypoints: `runner.py`, `serial_transport.py`, `mock_transport.py`, `virtual_encoder.py`, `cli.py`.
- Drift hotspots: ack mapping nuance, queue authority cache interpretation, fallback behaviors under budget/fault overrides.

### `gui/bench_app/`
- Entrypoints: `app.py`, `controller.py`.
- Drift hotspots: mixed transport/protocol-host command dispatch, UI state derivation from transport observations.

### `docs/openspec/v3/`
- Entrypoints: `state_machine.md`, `telemetry_schema.md`, `protocol/commands.json`, compliance matrices.
- Drift hotspots: stale test references, duplicated contracts.

### `tests/`
- Entrypoints: protocol, transport, telemetry, GUI, artifact parity suites.
- Drift hotspots: duplicate function names, governance/doc-link coverage gaps.

---

## Appendix B — Per-file annotation (top 30 files)

1. `src/coloursorter/protocol/host.py` — canonical command dispatcher + dedupe behavior.
2. `src/coloursorter/protocol/constants.py` — protocol constants and NACK code range.
3. `src/coloursorter/protocol/nack_codes.py` — canonical detail rules and helpers.
4. `src/coloursorter/protocol/policy.py` — mode transition matrix.
5. `src/coloursorter/protocol/authority.py` — authority pointer string.
6. `src/coloursorter/bench/serial_transport.py` — handshake/retry/state-sync and ack mapping.
7. `src/coloursorter/bench/mock_transport.py` — host-backed simulated transport parity.
8. `src/coloursorter/bench/runner.py` — cycle pipeline, telemetry emission.
9. `src/coloursorter/bench/types.py` — bench telemetry and transport response schema.
10. `src/coloursorter/bench/virtual_encoder.py` — trigger generation/projection model.
11. `src/coloursorter/bench/transport.py` — transport protocol interface.
12. `src/coloursorter/bench/esp32_transport.py` — serial adapter subclass.
13. `src/coloursorter/bench/cli.py` — runtime bench execution entrypoint.
14. `gui/bench_app/controller.py` — GUI state + protocol orchestration.
15. `gui/bench_app/app.py` — UI presentation and queue/fault rendering.
16. `gui/bench_app/ui_main_layout.ui` — widget topology authority (Qt Designer).
17. `gui/ui_main_layout.json` — runtime GUI layout mirror.
18. `docs/openspec/v3/protocol/commands.json` — protocol authority artifact.
19. `protocol/commands.json` — protocol mirror artifact.
20. `contracts/mcu_response_schema.json` — runtime response contract.
21. `docs/openspec/v3/contracts/mcu_response_schema.json` — spec mirror of response contract.
22. `contracts/mcu_response_schema_strict.json` — strict conditional contract.
23. `docs/openspec/v3/contracts/mcu_response_schema_strict.json` — strict mirror.
24. `docs/openspec/v3/state_machine.md` — mode/safe/queue authority doctrine.
25. `docs/openspec/v3/telemetry_schema.md` — telemetry field/timing doctrine.
26. `docs/openspec/v3/protocol_compliance_matrix.md` — requirement ↔ validation mapping.
27. `tests/test_protocol_compliance_v3.py` — protocol contract tests.
28. `tests/test_serial_transport.py` — transport robustness + mapping tests.
29. `tests/test_determinism_and_telemetry.py` — encoder/timing determinism tests.
30. `tests/test_openspec_artifacts.py` — artifact parity and mirror checks.

---

## Appendix C — Glossary normalization map

| Term in docs | Term in runtime/tests | Notes |
|---|---|---|
| `frame_timestamp` | `frame_timestamp_s` | Same concept; runtime suffix encodes units.
| `trigger_generation_timestamp` | `trigger_generation_s` | Same concept.
| `trigger_timestamp` | `trigger_timestamp_s` | Same concept.
| `queue depth truth` | `_last_queue_depth` (derived cache) | Cache is non-authoritative; ACK/GET_STATE authoritative.
| `SAFE` | `FaultState.SAFE` / `OperatorMode.SAFE` | Distinct fault vs operator-mode domains.
| `WATCHDOG` | `FaultState.WATCHDOG` + sometimes `nack_detail` text | Split semantic pathway.
| `mode authority host-owned` | `OpenSpecV3Host` + GUI `_set_protocol_mode` | GUI issues commands; host decides acceptance.

---

## Appendix D — Duplicate-authority map

| Authority domain | Primary | Mirror(s) | Why it matters |
|---|---|---|---|
| Protocol commands | `docs/openspec/v3/protocol/commands.json` | `protocol/commands.json` | Manual updates can desync wire contract.
| MCU response schema | `contracts/mcu_response_schema.json` | `docs/openspec/v3/contracts/mcu_response_schema.json` | Consumer/docs can diverge on required fields.
| Strict response schema | `contracts/mcu_response_schema_strict.json` | `docs/openspec/v3/contracts/mcu_response_schema_strict.json` | Conditional ACK/NACK constraints may drift.
| GUI layout | `gui/ui_main_layout.json` | `docs/openspec/v3/gui/ui_main_layout.json` | Operator docs/UI tooling may mismatch runtime UI.
| Runtime config defaults | `configs/default_config.yaml` | `docs/openspec/v3/configs/default_config.yaml` | Deployment defaults and docs parity risk.

