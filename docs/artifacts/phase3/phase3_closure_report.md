# Phase 3 Exit Checklist — Closure Report

Task: T3-006  
Audit focus: Reproducible gate evidence with explicit blocked-command reasons.

Overall readiness decision: **CONDITIONAL PASS**

- Mandatory host and bench gates executed in this environment: PASS.
- Windows firmware gate command is blocked in this Linux environment and is reported with exact blocker details.
- Coverage gate command is blocked due to missing pytest-cov plugin and is reported with exact blocker details.

## Subsystem viability status matrix
| Subsystem | Viability | Verification Scope Tag | Evidence Basis |
| --- | --- | --- | --- |
| bench | VIABLE | VERIFIED | Deterministic bench checks (`hil_repeatability`, `timing_envelope`, `trigger_correlation`) are PASS. |
| protocol host | VIABLE | VERIFIED | Protocol host parity check (`protocol_parity`) is PASS against deterministic protocol vectors. |
| live runtime | PARTIAL | NOT VERIFIED | No Phase 3 evidence in this bundle executes live runtime hardware-loop validation. |
| GUI | PARTIAL | NOT VERIFIED | No Phase 3 evidence in this bundle executes GUI transition/runtime parity validation. |

## Verification scope tags
- VERIFIED: Explicitly validated by a passing Phase 3 deterministic check in this bundle.
- NOT VERIFIED: Not directly validated by a passing Phase 3 deterministic check in this bundle.

## Fingerprints
- hil_repeatability: e503292449445b3a1908f6e42ff2d6cb5687b25a72503771fd6034bd0679015e
- protocol_parity: 3f63946102785e780a53f9acdec0515c55ed26ee5bcbaac258377e97508fc9c5
- timing_envelope: fb166d3b199dcde356617be8242a97644fe0f025c100d3544b31a32786ea57d9
- trigger_correlation: 69ddb1cbca2ea4c5db618da8f12dbe512bf8874f9cdf8632c3ffde1672c453f1
## Required gate checklist

| Gate | Command | Status | Notes |
| --- | --- | --- | --- |
| Firmware unit tests | `./run_tests.bat` | BLOCKED | Windows batch file is not executable in this Linux shell (`Permission denied`). |
| Host test suite | `pytest tests/` | PASS | Full suite completed with passing status. |
| Integration timing/trace checks | `pytest bench/` | PASS | Bench checks completed with passing status. |
| Coverage artifact gate | `pytest --cov=src/coloursorter --cov-report=xml` | BLOCKED | `pytest` in this environment does not have `pytest-cov` options available. |

## Exact command evidence

### 1) Firmware unit tests gate

Command:

```bash
./run_tests.bat
```

Exit code: `126`  
Status: **BLOCKED**

```text
/bin/bash: line 1: ./run_tests.bat: Permission denied
```

Blocker reason: This gate requires a Windows batch execution context (or equivalent wrapper) not available in the active Linux shell.

---

### 2) Host test suite gate

Command:

```bash
pytest tests/
```

Exit code: `0`  
Status: **PASS**

```text
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 45%]
..............................x......................................... [ 60%]
......................x................................................. [ 76%]
........................................................................ [ 91%]
.........................................                                [100%]
471 passed, 2 skipped, 2 xfailed in 11.59s
```

---

### 3) Integration timing/trace gate

Command:

```bash
pytest bench/
```

Exit code: `0`  
Status: **PASS**

```text
.                                                                        [100%]
1 passed in 0.02s
```

---

### 4) Coverage artifact gate

Command:

```bash
pytest --cov=src/coloursorter --cov-report=xml
```

Exit code: `4`  
Status: **BLOCKED**

```text
ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] [...]
pytest: error: unrecognized arguments: --cov=src/coloursorter --cov-report=xml
  inifile: /workspace/CVsorter/pyproject.toml
  rootdir: /workspace/CVsorter
```

Blocker reason: `pytest-cov` is unavailable in the environment; therefore `coverage.xml` cannot be produced by this command until coverage plugin dependencies are installed.

## Transition safety evidence (GUI controller)

Replay→Live illegal transition behavior is guarded and validated by tests to ensure:

- runtime state is unchanged,
- overlay text does not imply a successful state change,
- cycle timer/button states remain consistent,
- state machine trigger emission is still observable for transition requests.

Targeted test evidence:

```bash
pytest tests/test_bench_controller.py::test_illegal_replay_to_live_transition_keeps_runtime_ui_timer_consistent
```

(covered by `pytest tests/` PASS run above)

## Determinism/audit notes

- Commands and outputs above are recorded verbatim for reproducibility.
- Blocked commands are explicitly reported with exact stderr and root-cause rationale.
- No protocol/architecture frozen-contract files were modified for this artifact update.
