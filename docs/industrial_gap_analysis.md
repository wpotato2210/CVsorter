Prompt executed — deliverables below.

## 1) Per-file analysis

> Source baseline: local repository snapshot at commit `becd82fe0a697ea165f16545689138495d2eebc2` (used because requested `<hash>` was not provided). Missing files are treated as critical documentation/implementation gaps.

### Core specs
- **openspec.md** (SHA1 `32f193757fb0ad2a5d32dfcd793d110644b12cb1`)
  - Summary: index-style pointer document, not an executable industrial requirement spec.
  - Expected industrial spec: should define camera/encoder/actuator interfaces, timing budgets, safety states, and authenticated control contracts.
  - Gaps:
    - No explicit FPS=100, end-to-end latency ≤15 ms, or actuator pulse ≤1 ms budget.
    - No RGB+NIR camera definition or conveyor encoder coupling semantics.
    - No E-STOP behavior, fault latching, or watchdog escalation timing.
  - Priority: **High (Risk 9/10)**.
  - Recommendation:
    ```md
    Add normative sections: Hardware Interface Spec, Timing Budgets, Actuator Command Schema,
    Conveyor Encoder Sync, Telemetry/Health Schema, Security/Operator Controls,
    Calibration Protocol, Hardware State Machine.
    ```
  - HW/SW alignment: inconsistent with protocol/threading/MCU because required physical constraints are absent.

- **agents.md** (SHA1 `2f9469d97eab3a7307651f187313c87bcafe8890`)
  - Summary: process/agent orchestration notes.
  - Expected: traceability and governance links to safety-critical requirement ownership.
  - Gaps: no safety ownership matrix or change-control class for real-time/safety fields.
  - Priority: Medium.
  - Recommendation:
    ```md
    Add change-class tags: [SAFETY], [REALTIME], [PROTOCOL], with mandatory reviewer roles.
    ```

- **architecture.md** (SHA1 `c75b406a61197d849365354ef8bd4686fb0ebcb6`)
  - Summary: high-level architecture with bench focus.
  - Expected: explicit hardware pipeline from sensor timestamp to ejector pulse.
  - Gaps: lacks deterministic timing chain (camera->decision->actuator) and encoder phase model.
  - Priority: High (Risk 8/10).
  - Recommendation:
    ```md
    Add timing swimlane with deadlines per stage and encoder-referenced actuation formula.
    ```

- **filetree.md** (SHA1 `f1ddf0fa22502d1f053599c9448063015d4cf429`)
  - Summary: structure map.
  - Expected: should identify safety-critical binaries/configs/tests.
  - Gaps: no criticality tags, no generated-vs-source contract marker.
  - Priority: Medium.
  - Recommendation: annotate files with `criticality: safety|realtime|support`.

- **protocol.md** (SHA1 `ba2f1b10362b9044a0b92d54bf55e3cb3aff1bc7`)
  - Summary: frame format, handshake, command set.
  - Expected: authenticated anti-replay protocol with heartbeat QoS and timing guarantees.
  - Gaps:
    - CRC32 integrity only; no message authentication (MAC/signature).
    - Heartbeat lacks required period/jitter/timeouts as numeric constraints.
    - No actuator pulse width field constraints or encoder timestamp in command payload.
  - Priority: **High (Risk 9/10)**.
  - Recommendation:
    ```text
    Extend frame: <msg_id|ts_us|nonce|CMD|payload|HMAC-SHA256>;
    require heartbeat_period_ms<=50 and timeout_ms<=150.
    ```
  - Alignment check: command names align with `state_model.md`; timing/safety fields do not.

- **threading.md** (SHA1 `36b9e177dee081e024dbb9b40a69f611a6bfc242`)
  - Summary: Qt main-loop tick model, mostly single-threaded.
  - Expected: camera and actuator should be isolated workers with lockless transfer and watchdog supervision.
  - Gaps:
    - No explicit worker split for high-rate camera ingest vs deterministic actuator dispatch.
    - No SLO-bound queue handoff policy.
  - Priority: High (Risk 8/10).
  - Recommendation:
    ```md
    Define 3 workers: Capture(100 FPS), Decision, Actuation; SPSC ring depth=8; watchdog 100 ms.
    ```

- **CONTRIBUTING.md** (SHA1 `6973b56abf59e018ace7442793b76061750d156b`)
  - Summary: contributor basics.
  - Expected: safety/realtime contribution gate checklist.
  - Gaps: missing requirement for latency/safety regression evidence on protocol/state changes.
  - Priority: Medium.

- **deployment.md** (SHA1 `d83e1d01ba3d33122d9bde6dfde8bc7e77b8e0be`)
  - Summary: operational deployment model.
  - Expected: production network hardening + safety interlocks + telemetry retention SLOs.
  - Gaps: no mTLS/auth mechanism, no E-STOP hardware validation step, no max telemetry latency budget.
  - Priority: High (Risk 8/10).

- **data_model.md** (SHA1 `50218a74f665a4e29b78fa98fc7b4a735e3c75e1`)
  - Summary: canonical entities for pipeline and telemetry.
  - Expected: concrete field schemas with units and precision.
  - Gaps: acknowledges missing canonical telemetry schema; unit fields not fully typed.
  - Priority: High (Risk 7/10).

- **constraints.md** (SHA1 `dcc2597810a8e60a32fd4052fe2b0ef40ecd21b2`)
  - Summary: behavioral bounds for queue and commands.
  - Expected: hard numeric bounds for latency/jitter/pulse spacing.
  - Gaps: explicitly calls timing/servo constraints unresolved.
  - Priority: High (Risk 8/10).

- **state_model.md** (SHA1 `8d9ecd72455005935af7aacb0669a52f802dae1a`)
  - Summary: mode/queue/scheduler states.
  - Expected: full hardware state machine including E-STOP and fault latching.
  - Gaps: no E-STOP state, no DISPATCHING/AWAITING_ACK explicit substates, no timing guards.
  - Priority: High (Risk 8/10).

- **security_model.md** (SHA1 `abbb78a09cd1983f6c5418821c1d28c79feba703`)
  - Summary: threat/control model.
  - Expected: mandatory authN/authZ, key rotation, command signing, physical safety linkage.
  - Gaps: authentication model is unresolved/open question.
  - Priority: High (Risk 9/10).

- **threading_model.md** (SHA1 `bbbda8b32176dc9b402b3f8a4e901918231cabe7`)
  - Summary: synchronization ownership goals.
  - Expected: concrete primitive choices and deadline-aware contention policy.
  - Gaps: explicitly missing lock ownership and hard latency SLO.
  - Priority: High (Risk 8/10).

### Operator docs
- **USER_MANUAL.md** (SHA1 `8f522d63f04ae7dea788e3dc5bfdc49c6bf3fcc7`)
  - Summary: bench/runtime usage manual.
  - Expected: operator SOP including calibration, E-STOP drills, alarm handling.
  - Gaps: no explicit E-STOP validation procedure; no calibration acceptance thresholds.
  - Priority: High.

- **QUICK_START.md** (SHA1 `d8588682461a17a7e7a9bc9db5a020367d27b8cb`)
  - Summary: startup flow and sample config.
  - Expected: safe bring-up sequence with interlock checks.
  - Gaps: lacks hardware preflight checklist (encoder, pneumatic pressure, safety loop continuity).
  - Priority: Medium.

- **IMPLEMENTATION_REQUEST_TEMPLATE.md** (SHA1 `c81579cebf71536c45ecd4821e9cfaefeec8a09b`)
  - Summary: request template.
  - Expected: should force requirement ID, timing impact, and safety impact sections.
  - Gaps: no mandatory realtime/safety impact block.
  - Priority: Medium.

### Style & validation
- **styleguide.md** (SHA1 `8abe17e01915d4789b4cb1db896654a27afdaf58`): lacks unit-annotation convention (`ms`, `us`, `mm`) enforcement. Priority Medium.
- **error_model.md** (SHA1 `e8ed0846b8d1a839044da3118580aceff425e355`): has retry bounds but no fail-safe stop response-time requirement. Priority High.
- **testing_strategy.md** (SHA1 `bc9f096d62e74c19c8e7e7fc187db529cdd00ead`): covers correctness; lacks explicit latency ≤15 ms and pulse ≤1 ms acceptance tests. Priority High.

### Firmware MCU
- **firmware/mcu/src/main.c** (SHA1 `559a766bcf9e7d3174a9ee4b8ac9ab7c6a2e9a4d`): watchdog loop exists but no documented actuator timing path. Priority High.
- **firmware/mcu/src/scheduler.c** (SHA1 `cebb0f55bd35d7f3e76302c1e0d912e8b9f2f0c0`): queue ops are fast; lacks deadline metadata and enqueue timestamp for latency audit. Priority High.
- **firmware/mcu/include/scheduler.h** (SHA1 `d7a665376b76f8ad96af107d0c09dabdecede835`): minimal queue API; no priority/time fields. Priority Medium.
- **Missing**: `serial.c`, `serial.h`, `state_machine.c`, `state_machine.h` (not found). Priority **High (Risk 9/10)** due to traceability holes.

### GUI
- **Missing**: `mainwindow.ui/.cpp/.h`, `dashboard.py`, `icons.qrc` (not found). Priority High (operator/HMI evidence unavailable).

### Tools/utilities
- **Missing**: `calibrate_camera.py`, `log_parser.py`, `measure_latency.py`, `validate_schema.py` (not found). Priority High (validation tooling gap).

### Slides
- **Missing**: `architecture_overview.pdf`, `deployment_plan.pdf` (not found). Priority Low-Medium (stakeholder communication gap).

### Hardware/Software alignment + numeric/unit consistency
- Camera/actuator/conveyor/estop/queue/latency targets are **not consistently specified** across `openspec.md`, `protocol.md`, `threading.md`, `state_model.md`, and MCU C files.
- Only queue depth (`0..8`) is consistently referenced; FPS=100, latency ≤15 ms, and pulse ≤1 ms are absent in primary contracts.
- Unit precision is mixed/implicit (`ms` appears in retry notes, `us` in scheduler comments), with no global unit convention.

## 2) Cross-file consistency
- **Reference chain check (openspec→protocol→threading→MCU→GUI):**
  - openspec points to protocol contracts, but top-level spec omits industrial timing/safety constraints.
  - protocol and state model align on `mode/queue_depth/scheduler_state/queue_cleared` naming.
  - threading docs describe single-thread event-loop model; MCU assumes low-level queue operations but lacks shared timing contract.
  - GUI files requested for validation are missing, blocking end-to-end HMI consistency proof.
- **Mismatches flagged:**
  - Security model open question vs protocol using unauthenticated CRC frame.
  - State model lacks E-STOP state while deployment/manual discuss SAFE behavior.
  - Timing targets absent from core contract despite queue constraints being explicit.

## 3) Operator/GUIs workflow analysis
- Missing explicit calibration steps: no acceptance criteria for pixel/mm drift, lens focus, NIR alignment.
- Telemetry/alerts: docs mention telemetry but no canonical schema fields for alarm severity, E-STOP latch, pneumatic pressure, encoder health.
- E-STOP integration: SAFE mode exists conceptually, but no verified hardware stop loop, reset authority, or acknowledgment workflow.
- Dashboard schema parity cannot be fully verified due to missing requested GUI files.

## 4) Real-time performance evaluation
- Latency risk: single-thread Qt tick model implies camera pull + decision + transport + UI work in one cycle; may violate ≤15 ms under load.
- Throughput risk: queue depth fixed at 8 with no documented backpressure budget at 100 FPS.
- Actuation risk: no explicit pulse-width guard (≤1 ms) in protocol/state docs.
- Safety timing risk: watchdog exists in MCU main loop but no documented max detection-to-safe-halt latency.

## 5) Actionable code/config snippets

### Telemetry schema (JSON)
```json
{
  "$id": "telemetry.v1",
  "type": "object",
  "required": ["ts_us","mode","queue_depth","scheduler_state","latency_ms","estop_latched"],
  "properties": {
    "ts_us": {"type":"integer","minimum":0},
    "mode": {"enum":["AUTO","MANUAL","SAFE"]},
    "queue_depth": {"type":"integer","minimum":0,"maximum":8},
    "scheduler_state": {"enum":["IDLE","ACTIVE","DISPATCHING"]},
    "latency_ms": {"type":"number","maximum":15},
    "actuator_pulse_ms": {"type":"number","maximum":1.0},
    "fps": {"type":"number","minimum":100},
    "encoder_ok": {"type":"boolean"},
    "estop_latched": {"type":"boolean"}
  }
}
```

### Configuration schema (JSON)
```json
{
  "$id": "runtime_config.v1",
  "type": "object",
  "required": ["fps_target","pixel_per_mm","queue_depth","heartbeat_ms"],
  "properties": {
    "fps_target": {"const": 100},
    "pixel_per_mm": {"type":"number","const":0.25},
    "max_latency_ms": {"type":"number","const":15},
    "max_pulse_ms": {"type":"number","const":1},
    "queue_depth": {"type":"integer","const":8},
    "heartbeat_ms": {"type":"integer","maximum":50}
  }
}
```

### Protocol frame upgrade
```text
Legacy: <msg_id|CMD|payload|CRC32>
New:    <msg_id|ts_us|nonce|CMD|payload|HMAC_SHA256>
Rules: heartbeat every 50 ms; timeout 150 ms -> DEGRADED; 3 misses -> SAFE_LATCH.
```

### Threading pseudocode (lockless + watchdog)
```text
capture_worker@100fps:
  frame = cam.read(ts_us)
  if ring.full(): drop_oldest_and_alarm()
  ring.push(frame)

decision_worker:
  f = ring.pop_wait(2ms)
  trig = infer_and_schedule(f)
  cmdq.push(trig)

actuator_worker:
  t = cmdq.pop_wait(1ms)
  send_sched(t, encoder_ticks)
  assert ack.latency_ms <= 15
  assert pulse_ms <= 1

watchdog@50ms:
  if heartbeat_miss>=3 or estop_signal: force_safe_latch(); clear_queue()
```

## 6) Updated openspec.md draft

### Hardware Interface Spec
Purpose: define physical IO boundaries and deterministic control semantics.
Required fields: `camera.rgb`, `camera.nir`, `encoder.ticks_per_rev`, `actuator.type`, `estop.loop_ok`, `pneumatic.pressure_kpa`.

### Performance & Timing Budgets
Purpose: enforce real-time determinism.
Required fields: `fps_target=100`, `max_latency_ms<=15`, `max_actuator_pulse_ms<=1`, `heartbeat_ms<=50`, `queue_depth=8`.

### Actuator Command Schema
Purpose: normalized eject command.
Required fields: `lane`, `trigger_mm`, `pulse_ms`, `encoder_tick_ref`, `deadline_us`, `auth_tag`.

### Conveyor Sync & Encoder Model
Purpose: convert vision coordinates to conveyor-relative timing.
Required fields: `pixel_per_mm=0.25`, `belt_speed_mm_s`, `encoder_ticks_per_mm`, drift compensation factor.

### Telemetry / Health Schema
Purpose: observable health and postmortem traceability.
Required fields: `latency_ms`, `queue_depth`, `missed_heartbeats`, `estop_latched`, `pressure_kpa`, `camera_sync_error_px`.

### Security & Operator Controls
Purpose: prevent unauthorized motion.
Required fields: authenticated frames (HMAC), role gates for `SET_MODE`, dual-action reset for `SAFE_LATCH`.

### Calibration Protocols
Purpose: maintain metric accuracy.
Required fields: checkerboard/NIR alignment test, tolerance, timestamp, operator id, calibration hash.

### State Machine: hardware states
Purpose: safety-aware mode control.
Required states: `BOOT`, `READY`, `RUNNING`, `DEGRADED`, `SAFE_LATCH`, `ESTOP_ACTIVE`, `RECOVERY_PENDING`.

**Example JSON (≤40 lines):**
```json
{
  "hardware": {
    "camera": {"rgb": true, "nir": true, "fps_target": 100},
    "encoder": {"ticks_per_rev": 2048, "pixel_per_mm": 0.25},
    "actuator": {"type": "pneumatic", "max_pulse_ms": 1.0},
    "safety": {"estop_loop": true, "safe_latch_reset_role": "supervisor"}
  },
  "timing": {"max_latency_ms": 15, "queue_depth": 8, "heartbeat_ms": 50},
  "telemetry": {"required": ["latency_ms", "queue_depth", "estop_latched", "fps"]}
}
```

Minimal config defaults: FPS=100, pixel/mm=0.25, latency ≤15 ms, pulse ≤1 ms, queue depth=8.
Safety/security validation notes: reject unauthenticated motion commands; enforce E-STOP hardwired cut + software latch.

## 7) Unified diff (insertions only)
```diff
--- openspec.md
+++ openspec.md
@@
+## Hardware Interface Spec
+- camera: RGB+NIR, target_fps=100
+- conveyor encoder: ticks_per_rev (required), sync with frame timestamp
+- actuator: pneumatic ejector, max_pulse_ms<=1
+- safety: E-STOP hard loop + software SAFE_LATCH
+
+## Performance & Timing Budgets
+- end_to_end_latency_ms<=15
+- queue_depth_default=8
+- heartbeat_period_ms<=50; heartbeat_timeout_ms<=150
+
+## Actuator Command Schema
+- fields: lane, trigger_mm, pulse_ms, encoder_tick_ref, deadline_us, auth_tag
+
+## Conveyor Sync & Encoder Model
+- pixel_per_mm default 0.25
+- conversion path: frame_px -> mm -> encoder ticks -> dispatch deadline
+
+## Telemetry / Health Schema
+- latency_ms, fps, queue_depth, actuator_pulse_ms, estop_latched, pressure_kpa
+
+## Security & Operator Controls
+- authenticated frames (HMAC-SHA256), replay window via nonce+ts_us
+- role-gated SAFE reset and mode transitions
+
+## Calibration Protocols
+- RGB/NIR alignment and pixel_per_mm calibration with tolerance report
+
+## State Machine: hardware states
+- BOOT -> READY -> RUNNING -> DEGRADED -> SAFE_LATCH
+- any E-STOP assertion forces ESTOP_ACTIVE then SAFE_LATCH
```

## 8) Consolidated top-gap table

| Category | File | Gap | Priority | Short fix |
|---|---|---|---|---|
| Spec completeness | openspec.md | No hard realtime/safety requirements | High (9/10) | Add hardware/timing/security normative sections |
| Protocol security | protocol.md | CRC only, no auth/replay protection | High (9/10) | Add HMAC + nonce + timestamp |
| State safety | state_model.md | No E-STOP/SAFE_LATCH hardware state | High (8/10) | Extend state machine + transitions |
| Threading determinism | threading.md | Single-thread tick may breach latency | High (8/10) | Worker split + lockless queues |
| Concurrency contract | threading_model.md | Missing lock ownership + latency SLO | High (8/10) | Define primitives/deadlines |
| Numeric constraints | constraints.md | Timing/servo limits unresolved | High (8/10) | Add pulse/jitter/spacing limits |
| Telemetry schema | data_model.md | Field-level schema missing | High (7/10) | Publish canonical JSON schema |
| Security governance | security_model.md | AuthN/AuthZ unresolved | High (9/10) | Choose trust model + key mgmt |
| Validation coverage | testing_strategy.md | No explicit ≤15 ms / ≤1 ms tests | High (8/10) | Add latency/pulse acceptance tests |
| MCU traceability | firmware/mcu/src/* | Missing serial/state_machine files | High (9/10) | Restore or relink authoritative files |
| Operator safety SOP | USER_MANUAL.md | No E-STOP drill + reset workflow | High (8/10) | Add mandatory safety checklist |
| Tooling readiness | tools/* (missing) | No declared calibration/latency scripts | High (8/10) | Add/point to validated utility paths |

## 9) Automated bench tests
1. **LatencyBudget_E2E_100FPS**
   - Purpose: verify camera->decision->actuation latency budget.
   - Inputs: synthetic 100 FPS stream, queue depth=8, nominal transport RTT.
   - Expected: p99 latency ≤15 ms.
   - Pass/fail: fail if any 1-second window p99 >15 ms.

2. **ThroughputQueueStability_BurstLoad**
   - Purpose: ensure no uncontrolled backlog under burst triggers.
   - Inputs: 100 FPS, burst factor 1.5x for 10 s.
   - Expected: queue depth never >8; BUSY/NACK rate within defined threshold.
   - Pass/fail: fail if overflow or trigger reorder observed.

3. **SafetyResponse_ESTOP_Watchdog**
   - Purpose: validate stop-path determinism.
   - Inputs: assert E-STOP and heartbeat loss fault injections.
   - Expected: actuator disable + SAFE_LATCH within specified response window (define ≤50 ms).
   - Pass/fail: fail if any motion command accepted after latch.

## 10) Prioritized action plan
1. **Promote openspec to normative industrial contract** (Effort: Medium) — files: `openspec.md`, `constraints.md`, `state_model.md`.
2. **Harden protocol security and heartbeat semantics** (Effort: Medium) — files: `protocol.md`, `protocol/commands.json`, `security_model.md`.
3. **Implement deterministic worker architecture** (Effort: High) — files: `threading.md`, `threading_model.md`, `gui/bench_app/controller.py`, MCU scheduler/state modules.
4. **Standardize telemetry/config schemas and validators** (Effort: Medium) — files: `data_model.md`, `contracts/*.json`, `tools/*schema*`.
5. **Ship safety/latency acceptance suite and operator SOP updates** (Effort: Medium) — files: `testing_strategy.md`, `USER_MANUAL.md`, `QUICK_START.md`.

## 11) Machine-readable summary (YAML)
```yaml
gaps:
  - id: G1
    file: openspec.md
    risk: 9
    gap: "Missing hardware/timing/security normative requirements"
  - id: G2
    file: protocol.md
    risk: 9
    gap: "No authenticated frame format"
  - id: G3
    file: state_model.md
    risk: 8
    gap: "No E-STOP/SAFE_LATCH states"
  - id: G4
    file: threading.md
    risk: 8
    gap: "Single-thread model risks >15ms latency"
action_plan:
  - step: "Normative openspec sections"
    effort: medium
  - step: "Protocol auth + heartbeat SLA"
    effort: medium
  - step: "Worker split + lockless queue"
    effort: high
tests:
  - name: LatencyBudget_E2E_100FPS
    criterion: "p99 <= 15ms"
  - name: ThroughputQueueStability_BurstLoad
    criterion: "queue_depth <= 8"
  - name: SafetyResponse_ESTOP_Watchdog
    criterion: "safe_latch <= 50ms"
```
