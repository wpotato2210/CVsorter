# Multi-Lane Deterministic Routing V2 — Formal State Machine Specification

## 0. Scope and Execution Model
- Scope: per-bean routing/actuation state and per-station actuation state.
- Time base: encoder ticks only (`encoder_tick`).
- Concurrency model:
  - ISR writes encoder tick only.
  - Control task is single writer for `BeanState` and `StationState`.

## 1. Bean Routing State Machine

### 1.1 Bean States
| State | Definition |
|---|---|
| `UNINITIALIZED` | Bean exists but stable classification and lane assignment not both available. |
| `TRACKING` | Bean tracked; routing not yet frozen. |
| `ROUTE_FROZEN` | `target_lane` and `lane_delta_remaining` fixed; route immutable. |
| `AWAITING_TRANSFER` | Bean awaiting next eligible transfer opportunity. |
| `TRANSFER_RESERVED` | A station reservation exists for this bean and current step. |
| `TRANSFER_COMMITTED` | Reserved transfer has been committed to lane state. |
| `ROUTE_COMPLETE` | `lane_delta_remaining == 0`; bean is in target lane. |
| `ROUTE_INFEASIBLE` | No valid downstream sequence can complete required lateral movement. |
| `EXITED_SYSTEM` | Terminal state; bean passed conveyor endpoint. |

### 1.2 Bean Transition Table
| From | Event | Guard (boolean) | Actions | To |
|---|---|---|---|---|
| `UNINITIALIZED` | `EV_STABLE_CLASS_AND_LANE` | `stable_class == true && lane_known == true` | `init current_lane` | `TRACKING` |
| `TRACKING` | `EV_ROUTE_FREEZE` | `stable_class == true && lane_known == true && freeze_not_done == true` | `freeze_encoder_tick = encoder_tick; target_lane = resolve_target_lane(...); lane_delta_remaining = target_lane - current_lane; freeze_not_done = false` | `ROUTE_FROZEN` |
| `ROUTE_FROZEN` | `EV_EVAL_POST_FREEZE` | `lane_delta_remaining == 0` | `mark route done` | `ROUTE_COMPLETE` |
| `ROUTE_FROZEN` | `EV_EVAL_POST_FREEZE` | `lane_delta_remaining != 0` | `clear reservation refs` | `AWAITING_TRANSFER` |
| `AWAITING_TRANSFER` | `EV_TRANSFER_RESERVE_OK` | `lane_delta_remaining != 0 && station_exists_downstream == true && sign(lane_delta_remaining) == station.direction && current_lane == station.from_lane && abs(encoder_tick - fire_tick) <= station.trigger_window_ticks && bean_has_no_reservation == true` | `bind reserved_station_id; bind reserved_step_index` | `TRANSFER_RESERVED` |
| `AWAITING_TRANSFER` | `EV_NO_DOWNSTREAM_PATH` | `lane_delta_remaining != 0 && reachable_station_sequence_exists == false` | `emit FAULT_ROUTE_INFEASIBLE` | `ROUTE_INFEASIBLE` |
| `AWAITING_TRANSFER` | `EV_MISSED_TRIGGER_WINDOW` | `lane_delta_remaining != 0 && encoder_tick > fire_tick + station.trigger_window_ticks` | `emit EVT_MISSED_TRIGGER_WINDOW` | `AWAITING_TRANSFER` |
| `AWAITING_TRANSFER` | `EV_CONFLICT_LOSS` | `reservation_attempted == true && reservation_granted == false` | `emit EVT_STATION_CONFLICT_LOSS` | `AWAITING_TRANSFER` |
| `TRANSFER_RESERVED` | `EV_ACTUATION_PULSE_ISSUED` | `reservation_valid == true && abs(encoder_tick - fire_tick) <= station.trigger_window_ticks` | `pulse station actuator` | `TRANSFER_COMMITTED` |
| `TRANSFER_COMMITTED` | `EV_COMMIT` | `commit_not_applied == true` | `current_lane = current_lane + station.direction; lane_delta_remaining = lane_delta_remaining - station.direction; commit_not_applied = false; clear reservation refs` | `ROUTE_COMPLETE` if `lane_delta_remaining == 0` else `AWAITING_TRANSFER` |
| `ROUTE_COMPLETE` | `EV_ENDPOINT_REACHED` | `at_conveyor_endpoint == true` | `emit EVT_BEAN_EXITED` | `EXITED_SYSTEM` |
| `ROUTE_INFEASIBLE` | `EV_ENDPOINT_REACHED` | `at_conveyor_endpoint == true` | `apply fallback_policy; emit EVT_BEAN_EXITED_INFEASIBLE` | `EXITED_SYSTEM` |
| Any non-terminal | `EV_ENCODER_DISCONTINUITY` | `encoder_discontinuity_detected == true` | `emit FAULT_ENCODER_DISCONTINUITY; freeze scheduling for bean` | `ROUTE_INFEASIBLE` |
| `TRACKING` or `ROUTE_FROZEN` | `EV_CONFIG_INVALID` | `config_consistent == false` | `emit FAULT_CONFIG_INCONSISTENCY` | `ROUTE_INFEASIBLE` |

### 1.3 Bean Invariants
- `INV_B1`: In `ROUTE_FROZEN`, `AWAITING_TRANSFER`, `TRANSFER_RESERVED`, `TRANSFER_COMMITTED`, `ROUTE_COMPLETE`, `ROUTE_INFEASIBLE`, `target_lane` is immutable.
- `INV_B2`: `TRANSFER_RESERVED` implies exactly one active reservation per bean.
- `INV_B3`: `TRANSFER_COMMITTED` for (`bean_id`, `step_index`) can occur at most once.
- `INV_B4`: `lane_delta_remaining == target_lane - current_lane` after every commit.
- `INV_B5`: No transitions from `EXITED_SYSTEM`.

## 2. Transfer Station State Machine

### 2.1 Station States
| State | Definition |
|---|---|
| `IDLE` | Station available for reservation. |
| `RESERVED` | Station reserved for one bean within active trigger window. |
| `ACTUATING` | Output pulse in progress. |
| `BUSY` | Cooldown/busy window active; no new reservations accepted. |

### 2.2 Station Transition Table
| From | Event | Guard (boolean) | Actions | To |
|---|---|---|---|---|
| `IDLE` | `EV_STATION_RESERVE_REQUEST` | `bean_eligible == true && station_not_busy == true` | `set reserved_bean_id; set reserved_fire_tick` | `RESERVED` |
| `RESERVED` | `EV_SCHED_CONFIRM` | `abs(encoder_tick - reserved_fire_tick) <= trigger_window_ticks` | `arm actuator` | `ACTUATING` |
| `RESERVED` | `EV_WINDOW_MISSED` | `encoder_tick > reserved_fire_tick + trigger_window_ticks` | `emit EVT_MISSED_TRIGGER_WINDOW; clear reservation` | `IDLE` |
| `ACTUATING` | `EV_PULSE_DONE` | `pulse_complete == true` | `set busy_until_tick = encoder_tick + busy_window_ticks` | `BUSY` |
| `BUSY` | `EV_BUSY_ELAPSED` | `encoder_tick >= busy_until_tick` | `clear station transient state` | `IDLE` |

### 2.3 Station Invariants
- `INV_S1`: At most one `reserved_bean_id` when state=`RESERVED`.
- `INV_S2`: No reservation accepted in `BUSY`.
- `INV_S3`: One actuation pulse maximum per reservation.

## 3. Global Scheduler Rules

### 3.1 Deterministic Scheduling Order
- Iterate stations by ascending `station_encoder_tick`.
- For each station, evaluate eligible beans with `abs(encoder_tick - fire_tick) <= trigger_window_ticks`.
- Conflict resolution (total order):
  1. Lowest `fire_tick`
  2. Tie -> lowest `bean_id`

### 3.2 Atomicity Rules
- Reservation write and bean reservation binding occur atomically in control task.
- Commit write (`current_lane`, `lane_delta_remaining`, reservation clear) is atomic in control task.
- ISR performs no bean/station mutations.

## 4. Determinism Guarantees
- `G1` Target immutability: guaranteed by `INV_B1` and absence of target-lane write transitions post-freeze.
- `G2` At most one lateral move per station encounter: station `RESERVED->ACTUATING->BUSY` path plus `INV_S3`.
- `G3` No duplicate commits: `INV_B3` and `commit_not_applied == true` guard.
- `G4` No inter-station race: single-writer scheduler + atomic reservation/commit.
- `G5` No wall-clock dependency: all guards/actions use `encoder_tick` only.
- `G6` Trace determinism: fixed iteration and tie-break order produce identical outcomes for identical encoder/event traces.

## 5. Explicit Failure Conditions

### 5.1 Failure Event Map
| Failure Condition | Detection Guard | Transition/Handling | Emitted Event |
|---|---|---|---|
| Missed trigger window | `encoder_tick > fire_tick + trigger_window_ticks` | Bean remains/re-enters `AWAITING_TRANSFER`; station `RESERVED->IDLE` | `EVT_MISSED_TRIGGER_WINDOW` |
| Station conflict loss | `reservation_attempted == true && reservation_granted == false` | Bean stays `AWAITING_TRANSFER` | `EVT_STATION_CONFLICT_LOSS` |
| No downstream feasible path | `reachable_station_sequence_exists == false` | Bean `AWAITING_TRANSFER->ROUTE_INFEASIBLE` | `FAULT_ROUTE_INFEASIBLE` |
| Encoder discontinuity | `encoder_discontinuity_detected == true` | Bean to `ROUTE_INFEASIBLE`; scheduling frozen for bean | `FAULT_ENCODER_DISCONTINUITY` |
| Configuration inconsistency | `config_consistent == false` | Bean to `ROUTE_INFEASIBLE` or pre-admission reject | `FAULT_CONFIG_INCONSISTENCY` |

## 6. Verification Conditions (Acceptance Criteria)
- `VC1`: No transition writes `target_lane` after first entry to `ROUTE_FROZEN`.
- `VC2`: For any station, at most one bean can be in reservation at a time.
- `VC3`: For any bean-step key, commit count <= 1.
- `VC4`: `current_lane` changes only in `TRANSFER_COMMITTED` on `EV_COMMIT`.
- `VC5`: All timing guards reference encoder ticks; none reference wall-clock time.
- `VC6`: Replay of identical encoder/event sequence yields identical state/event outputs.
