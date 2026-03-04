# MVP Baseline Feature List (Manual-Confirmed Only)

| Priority | Feature (manual-confirmed) | Manual location reference | Operator value (one line) |
|---|---|---|---|
| P0 | Replay-mode bench execution from files (`--mode replay`, `--source`) | `USER_MANUAL.md` §2, §5, §6, §7, §10 | Enables deterministic, repeatable validation runs without requiring live hardware input. |
| P0 | Decision and scheduling pipeline (lane assignment, rejection reason, scheduled commands) | `USER_MANUAL.md` §2, §6 | Converts detections into actionable reject timing for core bench sorting validation. |
| P0 | Artifact production (summary, events, telemetry CSV, optional text report) | `USER_MANUAL.md` §2, §5, §6, §10, §12 | Provides traceable run evidence for pass/fail review, audits, and operator reporting. |
| P0 | Runtime configuration via bench/lane/calibration files | `USER_MANUAL.md` §5, §8 | Lets operators run standardized sessions with controlled, auditable parameters. |
| P1 | Built-in scenario threshold evaluator (`coloursorter-bench-cli`) | `USER_MANUAL.md` §5, §7, §10 | Gives fast readiness checks against nominal/stress/fault thresholds before deeper runs. |
| P1 | Detection provider selection/override (`opencv_basic`, `opencv_calibrated`, `model_stub`) | `USER_MANUAL.md` §6, §7 | Allows operator selection of detector mode appropriate to current validation intent. |
| P1 | Transport paths: mock transport and serial transport mode | `USER_MANUAL.md` §3, §6, §12 | Supports both deterministic simulation sessions and hardware-integration validation runs. |
| P2 | Optional GUI bench monitoring (`coloursorter-bench-gui`) with frame/state/log visibility | `USER_MANUAL.md` §2, §5, §9 | Improves real-time operator situational awareness during bench runs and troubleshooting. |
| P2 | Live-mode frame capture (`--mode live`, camera options) | `USER_MANUAL.md` §2, §7, §12 | Enables direct camera-based validation when replay data is insufficient. |
| P2 | Optional frame snapshots (`--enable-snapshots`) | `USER_MANUAL.md` §6, §7 | Preserves visual evidence for anomaly review and run documentation. |
