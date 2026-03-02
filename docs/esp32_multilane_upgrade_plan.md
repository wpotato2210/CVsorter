# ESP32 Multi-Lane CV Colour Sorter — Upgrade Plan (Design Revision Baseline)

## Assumptions and architecture constraints
- Keep upstream Python CV + ESP32 deterministic state machine split.
- Keep ESP32 as deterministic actuator scheduler (hard timing, low-jitter output), not heavy CV inference.
- Preserve current role split: Setup Operator (full), Production Worker (restricted).
- Scale target remains up to 22 lanes with bounded per-lane scheduling latency `<insert measured scheduler jitter ms>`.

## Open-source inspired patterns considered
- **Conveyor CV tracking repos (OpenCV + Python):** object tracking IDs + line-cross timing rather than frame-local triggers.
- **OpenMV / MCU vision sorter projects:** confidence thresholds + reject bin fallback for uncertain classes.
- **Pick-and-place / multi-actuator OSS controllers (ROS/PLC style):** event queues, actuator cooldown windows, and dead-time compensation.
- **Industrial HMI-style OSS dashboards:** role-based screens, recipe/profile locking, and guided fault recovery.

---

## Prioritized upgrade backlog (highest impact first)

| Priority | Upgrade Area | Description | Benefits / Expected Impact | Dependencies / Constraints | Effort / Risk |
|---|---|---|---|---|---|
| 1 | **Software** | **Per-lane track-and-trigger queue**: add lightweight object tracking IDs and time-to-actuation prediction per lane, replacing single-frame trigger dependence. | Higher hit accuracy under overlap/variable belt speed; fewer mistimed actuations; throughput stability at high lane occupancy. `<insert measured miss-timing rate %>` | Must remain deterministic and O(lanes + active_tracks); bounded queue length per lane; strict monotonic timestamp source. | **Medium / Medium** |
| 2 | **Hardware** | **Add post-actuation optical confirmation gate** (simple reflective/photoelectric sensor bank or camera line check) per lane group. | Closed-loop sort verification; enables automatic drift detection and correction; improves reliability KPIs. `<insert measured false-accept %>` | GPIO/ADC expansion and wiring complexity; debounce + contamination handling; ESP32 ISR budget and sampling cadence constraints. | **Medium / Medium** |
| 3 | **Software** | **Ambiguous-class policy engine**: confidence bands + “uncertain → recirculate/reject” class, with defect/foreign-object branch. | Reduces bad picks from uncertain predictions; safer handling of non-bean objects; improved quality consistency. `<insert measured ambiguity rate %>` | Needs calibrated probability outputs; rule table must be setup-only editable; deterministic fallback timing path required. | **Low / Low** |
| 4 | **Hardware** | **Controlled illumination module** (high-CRI LED bar + diffuser + shroud) and fixed exposure profile. | Better CV robustness to ambient changes; tighter color cluster separability; fewer day/night recalibrations. `<insert measured ΔE or class-separation metric>` | Mechanical integration space; thermal management; constant-current driver noise isolation from MCU/servo power rails. | **Medium / Low** |
| 5 | **Safety** | **Jam and overlap early-warning fusion**: combine motor current proxy + CV occupancy anomaly + no-progress timer. | Earlier jam detection, less mechanical stress, fewer cascading faults; improved recovery speed. `<insert measured jam detection latency ms>` | Requires clean sensor normalization and fault voting thresholds; avoid nuisance trips during startup transients. | **Medium / Medium** |
| 6 | **Software** | **Actuator timing optimization**: lane-specific travel-time calibration table + temperature/voltage compensation + cooldown guard windows. | Better actuator strike alignment; reduced double-fires and missed ejections; extends actuator life. | Requires periodic calibration routine; ESP32 timer granularity and interrupt load must remain bounded. | **Medium / Medium** |
| 7 | **Operator Experience** | **Role-based workflow hardening**: Production view with only Start/Stop/Ack + lane health; Setup view for tuning and recipe management. | Lower operator error; faster onboarding; safer change control in production. | Enforce RBAC in GUI and config write paths; audit trail storage overhead. | **Low / Low** |
| 8 | **Safety** | **Mid-cycle power loss recovery journal**: persistent ring-buffer of in-flight actuation intents and conveyor epoch ID. | Deterministic restart behavior; fewer unintended actuations after reboot; better incident traceability. | Flash wear management; atomic write strategy; boot-time state reconciliation rules. | **Medium / Medium** |
| 9 | **Software** | **Foreign-object/defect pre-filter** using shape heuristics + temporal consistency before color classification. | Better rejection of stones/debris and malformed beans; protects downstream quality. `<insert measured foreign-object catch rate %>` | Must be CPU-light in Python path; avoid latency spikes; requires labeled edge-case set. | **Low / Medium** |
| 10 | **Operator Experience** | **Guided recovery playbooks in GUI** for jam, dirty optics, lane disable, sensor fault, E-stop reset. | Faster MTTR; consistent recovery steps; fewer unsafe manual interventions. `<insert measured MTTR minutes>` | Needs clear state machine hooks and localized instructions; maintainable fault-code taxonomy. | **Low / Low** |

---

## Detailed implementation slices

### 1) Hardware upgrades
- Add modular **sensor daughterboard** for grouped lane confirmation (e.g., 4-lane blocks) to control I/O growth.
- Add **encoder (or virtual encoder from motor control)** for conveyor speed normalization feeding CV-to-actuation timing.
- Improve **optical path**: enclosed lighting tunnel, quick-clean cover, contamination indicator timer.
- Optional staged actuator enhancement: from open-loop servo to **solenoid/air-jet bank with known response curves** where mechanically feasible.

### 2) Software upgrades
- Introduce **deterministic event model**:
  - `capture_ts`, `lane_id`, `track_id`, `eta_to_nozzle_ms`, `confidence`, `decision_reason`.
- Build **per-lane bounded priority queues** with overflow policy (`drop_oldest_uncertain` preferred).
- Add **timing profiler hooks** for each pipeline stage with alert thresholds.
- Add **recipe profiles** (bean type, belt speed class, lighting profile) with checksum and rollback.

### 3) Safety and recovery upgrades
- Extend fault model with explicit states:
  - `JAM_SUSPECT`, `JAM_CONFIRMED`, `OPTICS_DIRTY`, `CONFIRMATION_MISMATCH`, `RECOVERY_PENDING`.
- Add **two-step restart interlock** after fault/power return:
  1. dry-run scheduler flush,
  2. operator confirmation + slow-speed validation cycle.
- Add periodic **proof-test prompts** (E-stop, confirmation sensor, actuator response window).

### 4) Operator experience upgrades
- Production dashboard widgets:
  - lane utilization heatmap,
  - reject reason Pareto,
  - live confidence band histogram,
  - fault countdown and next action.
- Setup tools:
  - guided calibration wizard,
  - “golden sample” validation run,
  - config diff + sign-off log.

---

## Validation metrics placeholders
- Throughput: `<insert measured beans/min total>` and `<insert per-lane beans/min p95>`.
- Actuation accuracy: `<insert hit rate %>`, `<insert mistime p95 ms>`.
- CV quality: `<insert precision/recall by class>`, `<insert ambiguous fraction %>`.
- Reliability: `<insert MTBF hours>`, `<insert false jam alarms/day>`.
- Recovery: `<insert MTTR minutes>`, `<insert successful auto-restart %>`.
- Operator: `<insert setup time reduction %>`, `<insert training time hours>`.

## Suggested rollout phases
1. **Phase A (low risk, high gain):** ambiguous policy engine, role-based UI hardening, guided recovery playbooks.
2. **Phase B:** per-lane track-and-trigger queue + timing profiler + lane calibration tables.
3. **Phase C:** controlled lighting + optical confirmation hardware pilot on subset of lanes.
4. **Phase D:** full confirmation feedback integration + power-loss journal + advanced jam fusion.

## Decision gates before full deployment
- Gate 1: deterministic timing budget met (`<insert max scheduling jitter ms>`).
- Gate 2: ambiguity policy reduces false sort by `<insert target %>` without throughput loss.
- Gate 3: confirmation feedback improves verified-sort KPI by `<insert target %>`.
- Gate 4: recovery workflow cuts MTTR by `<insert target %>` with zero unsafe restarts.
