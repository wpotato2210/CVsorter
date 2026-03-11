# Testing Strategy

## Purpose

Define layered deterministic test coverage for frame processing, queue behavior, mode transitions, scheduler projection, retry semantics, and MCU command emission under bench stress scenarios.

## Scope

- Protect runtime pipeline regressions.
- Verify protocol ACK/NACK behavior and queue invariants.
- Validate scheduler projection format: `SCHED:<lane>:<position_mm>`.

## Executable Test Commands

These commands are aligned with repository scripts:

| Environment | Command | Notes |
| --- | --- | --- |
| Linux/macOS | `scripts/run_tests.sh` | Runs docs guard, Python automation tests, firmware host tests, and coverage artifacts when tooling is available. |
| Windows | `scripts\\run_tests.bat` | Runs docs guard, Python tests, firmware host tests, and coverage artifacts when tooling is available. |
| Coverage (direct) | `PYTHONPATH=src python -m pytest tests/automation/python --cov=src/coloursorter --cov-report=xml:test_data/coverage/python/coverage.xml` | Equivalent coverage target used by `scripts/run_tests.sh` when `pytest-cov` is present. |

## Layered Test Model

### Unit

| Area | Deterministic Checks |
| --- | --- |
| Preprocess | Stable transform outputs for identical frames. |
| Eval/deploy | Stable decision payload generation. |
| Scheduler | Stable projection math and ordering. |
| Queue | FIFO ordering, bounded depth, atomic reset. |
| Protocol parser | Canonical validation and error mapping. |
| Retry logic | Stable retry count/interval/termination behavior. |

### Integration

| Path | Contract Checks |
| --- | --- |
| `preprocess -> eval` | Data shape/value continuity and deterministic decisions. |
| `eval -> scheduler` | Deterministic projection command generation. |
| `scheduler -> serial_interface` | Correct wire payload and ACK/NACK handling with mocked transport. |
| Queue propagation | State and depth continuity across module boundaries. |

### Bench E2E

| Scenario | Required Assertions |
| --- | --- |
| Full runtime pipeline | Correct command emission and mode enforcement (`AUTO`, `MANUAL`, `SAFE`). |
| Simulated transport failures | Retry behavior preserves queue invariants and ordering. |
| Deterministic synthetic streams | Stable outputs for identical replay inputs. |

## Mode and Queue Matrix

### Mode transitions

| From | To | Expected behavior |
| --- | --- | --- |
| `SAFE` | `AUTO` | Rejected |
| `SAFE` | `MANUAL` | Allowed |
| `AUTO` | `SAFE` | Queue cleared |
| `MANUAL` | `SAFE` | Queue cleared |

### Queue states to cover

- Empty
- Partial
- Full

All mode transitions must be validated across all queue states.

## Queue Invariants

- Queue never exceeds configured maximum depth.
- Queue ordering remains FIFO.
- `RESET_QUEUE` clears queue atomically.
- Scheduler does not consume from empty queue.
- Mode transitions that require clearing enforce queue clearing.

## Retry Semantics

### Eligibility

| Retryable | Non-retryable |
| --- | --- |
| Timeout (no response) | Protocol NACK for invalid command |
| Corrupted response frame | Argument validation failure |
| Transport/serial error | Illegal state transition |
|  | Out-of-range values |

### Required behavior

- Scheduler emits each command once.
- Transport owns retry attempts for in-flight command only.
- Retries do not requeue commands or change scheduler ordering.
- `RESET_QUEUE` cancels in-flight command and retries.
- Default retry policy check: interval `100 ms`, max attempts `3`.

## Protocol Negative Tests

Validate canonical NACK handling for:

- Malformed frame structure
- Invalid command arguments
- Out-of-range numeric values
- Unknown command identifiers

Assertions must verify NACK code and unchanged scheduler/queue state.

## Determinism Rules

- No wall-clock sleeps in unit/integration tests.
- Use simulated clocks, deterministic ticks, or virtual time advancement.
- Keep deterministic correctness tests separate from concurrency stress tests.

## Coverage Matrix

| Module | Invariant | Unit | Integration | Bench E2E |
| --- | --- | --- | --- | --- |
| `preprocess` | Deterministic frame transforms | ✓ | ✓ | ✓ |
| `deploy/eval` | Decision payload correctness | ✓ | ✓ | ✓ |
| `scheduler` | Canonical projection formatting | ✓ | ✓ | ✓ |
| `queue` | Bounded depth, atomic reset, FIFO | ✓ | ✓ | ✓ |
| `serial_interface` | Wire encoding and ACK/NACK parsing | ✓ | ✓ | ✓ |
| `protocol parser` | Validation and bounds checking | ✓ | ✓ | ✓ |
| `runtime controller` | `SAFE/AUTO/MANUAL` transition rules | ✓ | ✓ | ✓ |
| `retry logic` | Timeout/backoff semantics | ✓ | ✓ | ✓ |

## Dependencies

- `tests/` suite and fixtures
- `protocol.md` ACK/NACK behavior
- `constraints.md` numeric bounds and transition rules
- `deployment.md` staging/production parity testing

## Docs Lint Guard

Malformed wrapper markers and corrupted typography are blocked by:

- `python tools/check_docs_wrappers.py`

This check is executed by both test runner scripts.
