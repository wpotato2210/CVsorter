# T3-003 Trigger Correlation Test Design (Informational, Non-Release Gating)

## Scope

This note defines a deterministic placeholder test design for correlating:

1. accepted protocol command (`ACK`), and
2. terminal status evidence (`transport_acknowledged`, `actuator_command_issued`, `scheduler_window_missed`).

This artifact is intentionally **informational** and **non-release gating** until end-to-end runtime correlation IDs are finalized.

## Deterministic correlation contract (draft)

Correlation key (ordered fields):

- `msg_id` (string)
- `command` (string)
- `lane` (int)

For identical inputs, expected terminal status mapping must be identical and stable.

## Candidate status classes

- `terminal_acknowledged`: command accepted and transport+actuation completed.
- `terminal_missed_window`: command accepted but scheduler window missed.
- `terminal_not_observed`: command accepted but no terminal status observed in bounded window.

## Placeholder vector pack

Vectors are stored in:

- `tests/fixtures/trigger_correlation_t3_003.json`

Vector ordering is fixed and must not be randomized.

## Proposed executable checks (draft)

- Fixture schema/order validation (gating-safe).
- Deterministic key uniqueness validation (gating-safe).
- Runtime correlation reconciler behavior (future, currently informational/non-gating).

## Non-gating policy

Until Phase 3.3 implementation is complete, unresolved runtime reconciliation behavior is tracked by placeholder xfail tests and must not block release gating.
