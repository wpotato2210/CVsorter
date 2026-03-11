# Task 9 — Command-Producer Authentication Policy (Start)

## Scope
This document starts Task 9 by defining a deterministic command authentication policy for motion-capable control commands and a rollout/validation plan.

## Threat model
### Assets
- motion command integrity (SCHED, RESET_QUEUE, and any actuator-affecting commands)
- deterministic scheduler timing behavior
- safety state integrity (`SAFE_LATCH`, `ESTOP_ACTIVE`)

### Adversary capabilities
- can connect an unauthorized producer on the host side
- can replay previously captured valid command frames
- can inject malformed or delayed command bursts

### Out of scope
- physical bus compromise after trusted endpoint hardening
- key extraction from fully compromised operator workstation

## Policy decision
Chosen model: **shared-secret authenticated envelope for all motion-capable commands**, plus anti-replay fields and bounded validity windows.

Rationale:
- stronger than physical-link trust in mixed bench/deployment environments
- lower implementation cost and deterministic verification path compared to asymmetric signatures on MCU targets
- compatible with existing safety semantics (failed auth keeps or escalates safety latch states)

## Deterministic enforcement contract
### Envelope fields (required)
- `auth_id`: static producer identity
- `auth_ts_ms`: producer timestamp in milliseconds
- `auth_nonce`: strictly monotonic per `auth_id`
- `auth_tag`: deterministic MAC over canonical command payload + auth fields

### Verification rules (deterministic order)
1. Parse frame and required auth fields.
2. Validate `auth_id` exists in configured key map.
3. Validate `auth_ts_ms` is within configured bounded skew window.
4. Validate `auth_nonce` is greater than last accepted nonce for `auth_id`.
5. Validate `auth_tag` against canonical serialization.
6. On any failure: reject command, emit audit record, preserve/force safety latch policy.

### Timing and reliability constraints
- verification path must be bounded and non-blocking in real-time loops
- key lookup and nonce tracking must be O(1) per command under expected producer counts
- retries are explicit at caller layer; receiver does not perform hidden auto-retry

## Authz mapping
- motion commands: require authenticated producer role `operator`
- safety-clear operations: require role `supervisor`
- read-only state queries: may be allowed for authenticated `observer` role (no motion side effects)

## Implementation plan
1. Add canonical command serialization helper used by both producer and verifier.
2. Add shared-secret keyring config loader with deterministic key selection by `auth_id`.
3. Implement verifier module returning explicit result codes (`ok`, `unknown_id`, `stale_ts`, `replay_nonce`, `bad_tag`).
4. Integrate verifier into command ingress before scheduler admission.
5. Extend audit logging with auth result and safety transition reason.
6. Add bench traces for replay, stale timestamp, and malformed envelope scenarios.

## Validation checklist
- [ ] Valid authenticated command admitted with deterministic accept result.
- [ ] Unknown `auth_id` rejected and audited.
- [ ] Replay nonce rejected and audited.
- [ ] Stale timestamp rejected by bounded skew rule.
- [ ] Invalid MAC rejected and safety policy enforced.
- [ ] Read-only query role does not gain motion command authority.
- [ ] Bench run demonstrates reproducible pass/fail outcomes across repeated runs.

## Notes for follow-up patches
- If protocol field additions are required, this will require contract-governed updates and explicit approval before editing frozen protocol documents.
- This start document intentionally avoids changing frozen contract artifacts.
