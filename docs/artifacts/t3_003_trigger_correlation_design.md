# T3-003 Trigger Correlation Contract (Release Gating)

## Scope

T3-003 is a **strict deterministic release-gating task** for trigger correlation.

It validates that each accepted `SCHED` command maps to exactly one terminal status record in trace artifacts.

## Deterministic correlation contract

Correlation key (ordered fields):

- `msg_id` (string)
- `command` (string, must be `SCHED`)
- `lane` / `lane_index` (int)

Required behavior:

1. accepted `SCHED` command -> exactly one terminal status
2. duplicate terminal status for same correlation key -> hard failure
3. missing terminal status for any accepted `SCHED` key -> hard failure
4. identical fixture inputs -> identical reconciliation outputs

## Terminal status classes

- `terminal_acknowledged`: command accepted and transport+actuation completed.
- `terminal_missed_window`: command accepted but scheduler window missed.
- `terminal_not_observed`: command accepted but no terminal status observed in bounded window.

## Deterministic vector pack

Vectors are stored in:

- `tests/fixtures/trigger_correlation_t3_003.json`

Vector ordering is fixed and must remain deterministic.

## Executable gating checks

- `tests/test_phase3_t3_003_trigger_correlation.py`
  - strict 1:1 mapping for accepted `SCHED` commands
  - duplicate-key rejection
  - missing-terminal-status detection
- `tests/test_phase3_t3_003_trigger_reconciliation_start.py`
  - artifact reconciliation determinism across repeated runs
- `tests/test_phase3_t3_003_trigger_reconciliation_gate.py`
  - per-key terminal status uniqueness and completeness on artifact outputs

## Verification command

- `pytest tests/ -k "t3_003 and trigger and correlation"`
