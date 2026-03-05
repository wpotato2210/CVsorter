# High-Priority Baseline Bean Sorting Plan

## Manual-Confirmed Baseline Capabilities

| Priority | Capability | Source | Why it matters |
|---|---|---|---|
| P2 | Live-mode frame capture (`--mode live`, camera options) | `USER_MANUAL.md` §2, §7, §12 | Enables direct camera-based validation when replay data is insufficient. |
| P2 | Optional frame snapshots (`--enable-snapshots`) | `USER_MANUAL.md` §6, §7 | Preserves visual evidence for anomaly review and run documentation. |

## Phase 1 — Confirmed MVP Baseline Implementation

| Item | Scope (confirmed baseline) | Acceptance criteria |
|---|---|---|
| 1 | Replay-mode bench execution from files (`--mode replay`, `--source`) | Setup completion time from command start to first processed frame is **≤ 3 minutes** for a standard operator runbook session. |
| 2 | Runtime configuration via `configs/bench_runtime.yaml` + lane/calibration configs | Calibration success rate is **≥ 98%** across 50 consecutive replay sessions using the approved calibration file set. |
| 3 | Decision + scheduling pipeline (lane assignment, reject reason, scheduled commands) | End-to-end decision payload validity is **100% schema-compliant** with no missing lane/reject/schedule fields in acceptance logs. |
| 4 | Artifact generation (summary, events, telemetry CSV, optional text report) | Parameter-change audit completeness is **100%**: every runtime parameter override appears in emitted artifacts with timestamp and source. |
| 5 | Built-in scenario threshold evaluator (`coloursorter-bench-cli`) | Nominal/stress/fault scenario evaluation completes with **pass/fail output for all configured thresholds** and no skipped scenarios. |
| 6 | Detection provider selection/override (`opencv_basic`, `opencv_calibrated`, `model_stub`) | Provider override reliability is **100%**: selected provider matches runtime output metadata for all acceptance executions. |
| 7 | Mock transport and serial transport paths | Transport-path parity verified with **no protocol-shape mismatches** between mock and serial outputs for the same replay input set. |

## Deferred Enhancements (Non-Confirmed Ideas)

- Operator quick-actions for common recovery paths (pause/resume, safe-mode, reconnect).
- Inline artifact navigator (last run summary/events/telemetry access).
- Any idea not listed in the manual-confirmed baseline table is classified as a **deferred enhancement**.
