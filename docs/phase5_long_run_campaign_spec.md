# Phase 5 Long-Run Parity Campaign Specification (T5-003)

Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes).

## Purpose

Define a deterministic long-run parity campaign for Phase 5 release evidence.
The campaign verifies that fixed bench and live replay sessions produce stable parity outcomes across repeated runs.

## Guardrails

- No edits to runtime I/O, protocol framing, timing guarantees, or frozen architecture artifacts.
- All campaign inputs must be fixed before execution.
- All session ordering, naming, and storage paths must be deterministic.
- Any contract-impacting deviation must be raised as a separate change request.

## Campaign constants

| Variable | Value | Requirement |
|---|---:|---|
| `campaign_id` | `P5-LONG-RUN-PARITY-001` | Stable campaign identifier. |
| `session_count` | 12 | Total required sessions per execution window. |
| `sessions_per_fixture` | 3 | Repeats per fixture. |
| `fixture_count` | 4 | Fixed fixture pack cardinality. |
| `bench_seed_base` | 500300 | Base seed for bench sessions. |
| `live_seed_base` | 500600 | Base seed for live sessions. |
| `max_allowed_divergences` | 0 | No parity divergence is acceptable. |
| `max_allowed_missing_terminal_records` | 0 | Every accepted command must map to exactly one terminal record. |
| `max_allowed_trace_hash_mismatches` | 0 | Trace hash set must be stable across repeated runs. |
| `artifact_root` | `docs/artifacts/phase5/long_run_parity/` | Canonical artifact storage path. |

## Fixed fixture pack

Execute the same ordered fixture pack for every campaign window:

1. `protocol_vectors_t3_001`
2. `timing_jitter_t3_002`
3. `trigger_correlation_t3_003`
4. `bench_live_parity_t3_005`

Fixture order is frozen for deterministic replay and naming.

## Session matrix

| Session ID | Fixture | Environment | Seed |
|---|---|---|---:|
| `P5-LRP-001` | `protocol_vectors_t3_001` | `bench` | 500301 |
| `P5-LRP-002` | `protocol_vectors_t3_001` | `live` | 500601 |
| `P5-LRP-003` | `protocol_vectors_t3_001` | `bench` | 500302 |
| `P5-LRP-004` | `timing_jitter_t3_002` | `bench` | 500303 |
| `P5-LRP-005` | `timing_jitter_t3_002` | `live` | 500602 |
| `P5-LRP-006` | `timing_jitter_t3_002` | `bench` | 500304 |
| `P5-LRP-007` | `trigger_correlation_t3_003` | `bench` | 500305 |
| `P5-LRP-008` | `trigger_correlation_t3_003` | `live` | 500603 |
| `P5-LRP-009` | `trigger_correlation_t3_003` | `bench` | 500306 |
| `P5-LRP-010` | `bench_live_parity_t3_005` | `bench` | 500307 |
| `P5-LRP-011` | `bench_live_parity_t3_005` | `live` | 500604 |
| `P5-LRP-012` | `bench_live_parity_t3_005` | `bench` | 500308 |

## Acceptance metrics

A campaign passes only when all metrics are satisfied:

1. **Parity decision stability:** `decision`, `reason`, `mode`, `queue_depth`, and `scheduler_state` remain identical for paired bench/live sessions.
2. **Terminal trace completeness:** each accepted command maps to exactly one terminal status record.
3. **Deterministic replay stability:** repeated sessions for the same fixture and environment produce identical trace hashes.
4. **Timing envelope conformance:** all replayed sessions remain within the existing Phase 3 and Phase 4 timing envelopes; no new timing thresholds are introduced here.
5. **Artifact completeness:** each session writes the required manifest, summary, trace, and hash outputs into the canonical storage path.

## Required artifacts per session

Each session directory must contain exactly these files:

- `manifest.json`
- `summary.json`
- `trace.log`
- `trace.sha256`

## Storage layout

Use the canonical storage layout below without variation:

```text
docs/artifacts/phase5/long_run_parity/
  campaign_manifest.json
  P5-LRP-001/
    manifest.json
    summary.json
    trace.log
    trace.sha256
  ...
  P5-LRP-012/
    manifest.json
    summary.json
    trace.log
    trace.sha256
```

## Review record

Record the following for every execution window:

- execution date (UTC)
- operator
- reviewed fixture pack digest
- pass/fail verdict
- divergence count
- terminal record mismatch count
- trace hash mismatch count
- artifact root path

## Non-goals

- No runtime code changes.
- No protocol/schema modifications.
- No redefinition of existing timing guarantees.
- No random fixture selection.
