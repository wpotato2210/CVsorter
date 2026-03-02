## ESP32 Multi-Lane CV Sorting Upgrade Assessment

### Suitability Summary
- Suitable for production deployment **if** deterministic state handling, per-lane isolation, watchdog enforcement, and measured timing margins are validated.

### Deterministic State Machine

#### Top-Level States
| Current State | Trigger | Guard/Condition | Action(s) | Next State |
|---|---|---|---|---|
| `Idle` | Start command | Safety chain healthy; enabled lanes healthy | Initialize lane contexts, arm frame pipeline, clear transient alarms | `Sorting` |
| `Idle` | Enter maintenance | Conveyor stopped; Setup Operator authorized | Lock production controls; enable maintenance panel | `Maintenance` |
| `Idle` | E-Stop pressed | None | Immediately de-energize all actuators; latch safety fault | `Emergency Stop` |
| `Sorting` | Stop command | Authorized role | Stop accepting new decisions; deterministically drain in-flight queue; stop conveyor | `Idle` |
| `Sorting` | Critical fault detected | Non-recoverable in-run fault | Stop conveyor; disable affected/all actuators by policy; latch fault code | `Error` |
| `Sorting` | E-Stop pressed | None | Immediate actuator disable; conveyor stop; latch safety fault | `Emergency Stop` |
| `Error` | Clear error | Setup Operator authorized; root cause cleared | Reset fault latch; reinitialize affected lane(s) | `Idle` |
| `Error` | E-Stop pressed | None | Immediate actuator disable; latch safety fault | `Emergency Stop` |
| `Emergency Stop` | E-Stop reset + safety acknowledge | Setup Operator authorized; physical chain healthy | Keep actuators disabled until explicit start; re-home required mechanics | `Idle` |
| `Maintenance` | Exit maintenance | Setup Operator authorized; no active maintenance fault | Reapply production config; remain stopped until explicit start | `Idle` |
| `Maintenance` | E-Stop pressed | None | Immediate actuator disable; latch safety fault | `Emergency Stop` |

#### Per-Lane Sub-States (`Sorting`)
| Lane Sub-State | Trigger | Guard/Condition | Action(s) | Next Sub-State |
|---|---|---|---|---|
| `LaneReady` | `frame_ready(i)` | Frame timestamp valid | Run CV inference for lane ROI; assign class + confidence | `Classified` |
| `Classified` | Classification routable | Confidence ≥ threshold; class routable | Compute delay from transport model; enqueue actuator event | `ActuationScheduled` |
| `Classified` | Ambiguous classification | Confidence < threshold OR overlap/conflict detected | Mark item ambiguous; raise per-lane GUI flag/counter; suppress unsafe actuation | `AmbiguousHold` |
| `ActuationScheduled` | Trigger time reached | Lane healthy; actuator available | Emit actuator command pulse/window | `AwaitWatchdog` |
| `AwaitWatchdog` | Watchdog pass | Command timing within window | Record success metrics | `LaneReady` |
| `AwaitWatchdog` | Watchdog timeout/miss | Late/missed trigger beyond tolerance | Latch lane fault; increment fault counter; apply stop policy | `LaneError` |
| `AmbiguousHold` | Worker clears ambiguous item | Production Worker authorized; lane clear | Clear lane ambiguous flag; log event | `LaneReady` |
| `AmbiguousHold` | Lane reset | Setup Operator authorized | Reset lane buffers/counters | `LaneReady` |
| `LaneError` | Lane reset | Setup Operator authorized; cause cleared | Reinitialize lane scheduler/watchdog | `LaneReady` |
| Any sub-state | Jam detected | Jam condition true | Stop impacted lane/group; raise per-lane alarm | `LaneError` |

**Deterministic semantics**
- Safety transitions preempt all non-safety transitions.
- Event processing order per cycle: **Safety IRQ → power integrity → actuator deadlines → frame/classification events → GUI commands**.
- Ambiguous items are never silently dropped; they are surfaced and resolved per lane.

### Safety Strategy
- **Emergency Stop:** immediate hardware-level disable of all actuator outputs.
- **Power loss:** persist atomic recovery record (`top_state`, per-lane sub-state, pending triggers, active faults) to NVS with CRC/versioning; reboot to safe non-actuating state; require explicit restart.
- **Actuator watchdogs:** per-lane deadline monitors detect missed/late triggers and force deterministic lane fault handling.

#### Risk Mitigation Table
| Risk Category | Failure Mode | Effect | Detection | Mitigation | Residual Policy |
|---|---|---|---|---|---|
| Hardware | E-Stop circuit fault | Unsafe continued motion | Startup + periodic safety self-test | Dual-channel safety chain; fail-safe relay logic | Block start; force `Error` |
| Hardware | Actuator stuck-on | Continuous/wrong actuation | Pulse-width/output timeout monitor | Hardware interlock timeout; disable lane driver | Stop lane/group |
| Timing | CV latency spike | Missed actuation window | Per-lane deadline monitor | Bounded queues; convert missed deadline to ambiguous | Raise lane alarm |
| Timing | 22-lane scheduler overload | Jitter/race risk | Control-cycle monitor | Priority scheduling; per-lane ring buffers; backpressure | Throughput de-rate |
| Operator misuse | Unauthorized maintenance action | Unsafe state/config change | RBAC + command authorization logs | Role-restricted GUI | Reject + log |
| Operator misuse | Wrong-lane ambiguous clear | Mis-sort risk | Lane-scoped UI action checks | Lane ID confirmation + active-lane interlock | Re-hold/reclassify |
| Environmental | Lighting drift | Classification drift | Confidence trend monitoring | Controlled lighting + calibration profiles | Ambiguity rate alert |
| Environmental | Leaves/non-bean objects | False class | Unknown/outlier detection | Route to ambiguous/manual handling policy | Manual review |
| Mechanical | Dirt/jam | Throughput loss; mistiming | Jam heuristics/current proxy/timing anomalies | Cleaning schedule + jam SOP | Lane stop + maintenance |
| Power | Mid-cycle power loss | Unknown in-flight actions | Brownout interrupt + persisted recovery record | Safe restart; stale trigger invalidation | No auto-actuation on reboot |

### Operator Workflow (Role-Based GUI)
| Function | Production Worker | Setup Operator |
|---|---|---|
| Start/Stop sorting | ✅ | ✅ |
| View per-lane status/errors | ✅ | ✅ |
| Clear ambiguous item per lane | ✅ | ✅ |
| Acknowledge non-critical lane alarms | ✅ (limited) | ✅ |
| Lane reset/reinitialize | ❌ | ✅ |
| Enter/exit maintenance mode | ❌ | ✅ |
| Edit thresholds/calibration/config | ❌ | ✅ |
| Safety reset after E-Stop | ❌ | ✅ (with physical reset prerequisite) |

### Timing Budget (Measured Value Placeholders)
| Segment | Symbol | Budget/Measured Value | Notes |
|---|---|---|---|
| Frame acquisition | `T_acq` | `<insert measured ms>` | Camera capture + DMA + buffer handoff |
| CV processing (per frame) | `T_cv` | `<insert per-frame ms>` | Preprocess + inference + postprocess |
| Actuator command execution | `T_act` | `<insert per-trigger ms>` | Dispatch + pulse/window generation |
| Conveyor transport (segment) | `T_conv` | `<insert per-segment ms>` | Capture-to-actuation travel time |
| Multi-lane concurrency overhead | `T_lane_overhead` | `<insert per-lane ms>` | Scheduler + queue arbitration overhead |
| Safety interrupt reaction | `T_safety_irq` | `<insert max ms>` | IRQ-to-actuator-disable latency |

#### Deterministic Timing Constraints
- `T_acq + T_cv + T_lane_overhead + T_act <= T_conv - Margin_lane`
- `max_cycle_time(N_active_lanes) <= <insert control-loop max ms>`
- `T_safety_irq <= <insert max ms>` (hard limit)

#### Worst-Case Validation Targets
- Overlapping beans/objects.
- Ambiguous classification bursts across lanes.
- Conveyor jam and trigger invalidation under load.
- Peak concurrency at 22 lanes.

### Edge Cases
| Edge Case | Deterministic Handling |
|---|---|
| Mid-cycle power loss | Persist recovery record atomically; reboot to safe non-actuating state; require explicit operator restart; invalidate stale trigger queue by timestamp tolerance. |
| Multi-lane conveyor jam | Detect per lane/group; halt impacted motion path; suppress pending triggers for impacted lanes; raise lane-specific alarms; allow Setup Operator lane reset. |
| Overlapping beans/objects | Mark as ambiguous/unknown; suppress speculative unsafe actuation; surface per-lane GUI item for worker clear/setup review. |
| Dirt accumulation affecting mechanics | Raise maintenance alert from jam/watchdog trends; require maintenance cleaning/reset before full-speed resume. |
