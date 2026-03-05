# Phase 1 Readiness Assessment

## Scope used for Phase 1 definition
Phase 1 requirements are taken from `docs/high_priority_baseline_bean_sorting_plan.md` (items 1-7 under "Phase 1 — Confirmed MVP Baseline Implementation").

## Automated checks performed

| Check | Command | Result | Notes |
|---|---|---|---|
| Install package editable | `python -m pip install -e . --no-build-isolation` | PASS | Build/install works with preinstalled dependencies. |
| CI parity: import | `python -c "import coloursorter"` | PASS | Matches CI import-integrity intent. |
| CI parity: protocol guard | `python tools/protocol_static_guard.py` | PASS | Static protocol checks passed. |
| CI parity: firmware readiness (strict) | `python tools/firmware_readiness_check.py --strict` | PASS | Strict readiness gate passed. |
| Hardware workflow parity: PySide6 module check | `python tools/validate_pyside6_modules.py` | PASS | Runtime module presence passed. |
| Hardware workflow parity: strict readiness report | `python tools/hardware_readiness_report.py --strict` | PASS | Overall status PASS. |
| Full unit/integration test suite | `pytest -q` | FAIL | 1 failing test in serial transport queue-depth handling. |

## Phase 1 deliverable verification matrix

| Item | Requirement (Phase 1) | Verification status | Evidence type |
|---|---|---|---|
| 1 | Replay-mode bench execution (`--mode replay`, `--source`) with <=3 minute setup | PARTIAL | CLI/documentation flags exist; setup-time SLA not auto-measured in this run. |
| 2 | Runtime config and calibration reliability >=98% over 50 sessions | PARTIAL | Config assets exist and quality-gate logic exists; no automated 50-session replay run executed here. |
| 3 | Decision + scheduling payload validity 100% schema-compliant | PARTIAL | Pipeline/scheduler tests exist; no dedicated acceptance-log corpus validation run captured here. |
| 4 | Artifact generation with 100% parameter-change audit completeness | PARTIAL | Phase-1 baseline evaluator includes artifact completeness gate; not executed against real acceptance artifacts here. |
| 5 | Scenario threshold evaluator reports pass/fail for all configured thresholds | PARTIAL | Evaluator tests present and baseline gate logic exists; end-to-end scenario pack execution not captured here. |
| 6 | Detection provider override reliability =100% across acceptance runs | PARTIAL | Provider set and provider tests exist; acceptance-run reliability across full executions not measured here. |
| 7 | Mock vs serial transport parity with zero protocol-shape mismatches | PARTIAL/AT-RISK | Transport parity is encoded in baseline gate, but current full suite has a serial transport regression failure. |

## Blockers and gaps

1. **Automated close blocker:** full test suite is not green (`pytest -q` has one failure).
2. Several Phase 1 acceptance criteria are quantitative and tied to repeated acceptance executions/artifact corpus validation; those are not fully auto-verifiable from static repo state alone without running controlled replay campaigns.

## Manual review still required

1. Confirm the standard operator runbook setup-time measurement method and capture repeatable timings for item 1.
2. Execute and record a 50-session calibration campaign with approved calibration set for item 2.
3. Validate acceptance logs/artifacts from representative nominal/stress/fault runs to confirm items 3-6 quantitatively.
4. Review whether the failing serial transport test reflects a true production parity risk or a stale/incorrect test expectation.

## Readiness decision

**Phase 1 status: NOT READY TO CLOSE.**

Reason: the all-tests-pass gate is currently failing and multiple quantitative acceptance criteria remain only partially automated in this assessment run.
