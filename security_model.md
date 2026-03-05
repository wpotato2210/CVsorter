# security_model.md

## Authn/authz baseline
- Motion-capable operations require authenticated command envelope (`auth_id`, `auth_ts_ms`, `auth_nonce`, `auth_tag`).
- Reset authority for clearing `SAFE_LATCH` is restricted to authorized operator role.

## Anti-replay
- Reject duplicate nonce for same `auth_id`.
- Reject stale `auth_ts_ms` outside watchdog-aligned validity window.
- Replays and auth failures keep or force `SAFE_LATCH`.

## Safety escalation semantics
- Heartbeat timeout (`>150ms`) escalates to `ESTOP_ACTIVE` and `SAFE_LATCH`.
- During `ESTOP_ACTIVE` or `SAFE_LATCH`, scheduler admission for motion commands is denied.
- Audit trail must include auth result, replay decision, and resulting safety transition.
