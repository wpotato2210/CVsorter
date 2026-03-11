# Engineering Grade Audit — CVsorter

Date: 2026-03-11  
Auditor: Codex (GPT-5.2-Codex)

## 1) Audit Scope

This audit evaluates repository engineering readiness against deterministic CV sorter requirements:

- deterministic runtime behavior
- protocol and contract conformance
- test harness health
- firmware/host parity safeguards
- reproducibility constraints

## 2) Methods

Executed checks:

1. `bash scripts/run_tests.sh`
2. `pytest -q`
3. `python tools/firmware_readiness_check.py --strict`

## 3) Executive Outcome

Status: **CONDITIONALLY READY**

- Baseline project checks pass under constrained environment (`scripts/run_tests.sh` reports PASS with explicit skips).
- Full `pytest` run reveals one deterministic blocking defect in runtime-config readiness validation.
- Firmware readiness strict gate currently fails due to runtime import coupling mismatch.

## 4) Findings

| ID | Severity | Finding | Evidence | Impact | Recommended Action |
|---|---|---|---|---|---|
| F-001 | High | `firmware_readiness_check` injects a stub `coloursorter.deploy` missing `resolve_detection_provider_name`, while runtime config now imports that symbol. | `check_runtime_config` injects only `DETECTION_PROVIDER_VALUES`; runtime config imports both symbols. | Strict firmware readiness gate fails; one repo test fails; CI confidence degraded. | Update readiness tool stub to provide `resolve_detection_provider_name` deterministic resolver (or stop stubbing and import deploy module safely). |
| F-002 | Medium | Test orchestration includes network-dependent dependency install path that can fail in offline/proxy-limited environments, then soft-skips. | `scripts/run_tests.sh` dependency install failed due proxy; script proceeds. | Reduced reproducibility signal in restricted environments. | Add documented offline test profile and pinned local wheel cache workflow. |
| F-003 | Low | Firmware host gtest suite is skippable when toolchain absent. | `scripts/run_tests.sh` reports firmware tests skipped without host gtest/CMake dependency. | Coverage gap for firmware logic on some hosts. | Add explicit readiness badge/status in CI matrix and fail only in required firmware lanes. |

## 5) Determinism Assessment

- No nondeterminism introduced during audit.
- Observed failure is import-contract drift, not stochastic behavior.
- Existing repository direction remains aligned with deterministic pipeline philosophy.

## 6) Gate Summary

| Gate | Result | Notes |
|---|---|---|
| Docs wrapper lint | PASS | Via `scripts/run_tests.sh`. |
| Python tests (script subset) | PASS | 5 passed under script path. |
| Full Python tests (`pytest -q`) | FAIL | 1 failure (`test_firmware_readiness_check_script_passes`). |
| Firmware readiness strict | FAIL | Runtime-config validator import mismatch. |
| Firmware gtest lane | SKIPPED | Missing host dependency in current environment. |

## 7) Required Fix Before “Engineering Grade Pass”

1. Patch `tools/firmware_readiness_check.py` runtime stub to include:
   - `resolve_detection_provider_name(name: str) -> str`
   - deterministic validation behavior matching `coloursorter.deploy` contract.
2. Re-run:
   - `python tools/firmware_readiness_check.py --strict`
   - `pytest -q`
3. Confirm zero failing tests.

## 8) Final Audit Verdict

**Current verdict: NOT YET FULL PASS** (single high-severity gating defect).  
**Expected post-fix verdict: PASS**, assuming no additional regressions.
