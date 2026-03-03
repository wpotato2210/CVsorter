# MVP Baseline Feature List (Manual-Confirmed Only)

| Priority | Feature (manual-confirmed) | Manual location | Operator value (one line) |
|---|---|---|---|
| P0 | Replay-mode bench execution from files (`--mode replay`, `--source`) | `USER_MANUAL.md` §2, §5, §7, §10 | Enables deterministic, repeatable validation runs without requiring live hardware input. |
| P0 | Decision + scheduling pipeline (lane assignment, reject reason, scheduled commands) | `USER_MANUAL.md` §2, §6 | Delivers the core sorting decision flow needed to convert detections into actionable reject timing. |
| P0 | Artifact generation (summary, events, telemetry CSV, optional text report) | `USER_MANUAL.md` §2, §6, §10, §12 | Provides traceable run evidence for pass/fail review and operator reporting. |
| P0 | Runtime configuration via `configs/bench_runtime.yaml` + lane/calibration configs | `USER_MANUAL.md` §5, §8 | Lets operators run standardized sessions with controlled, auditable parameters. |
| P1 | Built-in scenario threshold evaluator (`coloursorter-bench-cli`) | `USER_MANUAL.md` §5, §7, §10 | Gives fast readiness checks against nominal/stress/fault thresholds before deeper runs. |
| P1 | Detection provider selection/override (`opencv_basic`, `opencv_calibrated`, `model_stub`) | `USER_MANUAL.md` §6, §7 | Allows operators to choose the detector mode that matches current bench validation intent. |
| P1 | Mock transport and serial transport paths | `USER_MANUAL.md` §6, §3, §12 | Supports both deterministic simulation workflows and hardware-integration test sessions. |
| P2 | Optional GUI bench monitoring (`coloursorter-bench-gui`) with frame/state/log visibility | `USER_MANUAL.md` §2, §5, §9 | Improves live operator situational awareness during bench runs and troubleshooting. |
| P2 | Live-mode frame capture (`--mode live`, camera options) | `USER_MANUAL.md` §2, §7, §12 | Enables direct camera-based validation when replay data is insufficient. |
| P2 | Optional frame snapshots (`--enable-snapshots`) | `USER_MANUAL.md` §6, §7 | Preserves visual evidence for anomaly review and run documentation. |
