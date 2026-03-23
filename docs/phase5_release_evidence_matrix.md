# Phase 5 Release Evidence Matrix Template (T5-001)

Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes).

## Purpose

Define a deterministic release-evidence matrix template for Phase 5 governance.
The template freezes required evidence artifacts, approval ownership, acceptance thresholds, and review cadence without changing runtime behavior.

## Guardrails

- No edits to runtime behavior, protocol framing, timing guarantees, or frozen architecture artifacts.
- No changes to bench/live execution semantics are introduced by this template.
- Evidence naming, ordering, and storage references must remain deterministic.
- Any requested threshold that conflicts with an existing contract must be raised as a separate contract-change request.

## Template constants

| Variable | Value | Requirement |
|---|---|---|
| `matrix_id` | `P5-REL-EVIDENCE-001` | Stable matrix identifier for release governance records. |
| `phase` | `Phase 5` | Governs planning-only Phase 5 release evidence. |
| `artifact_root` | `docs/artifacts/phase5/release_evidence/` | Canonical evidence storage root. |
| `minimum_required_rows` | 6 | Every release packet must populate all canonical evidence rows. |
| `max_missing_artifacts` | 0 | No required artifact may be absent at review time. |
| `max_unapproved_rows` | 0 | All rows require explicit owner approval before release sign-off. |
| `review_cadence` | `per release candidate + weekly while open` | Mandatory governance review timing. |
| `status_values` | `not_started | in_progress | ready_for_review | approved | blocked` | Allowed deterministic status set. |

## Canonical evidence matrix template

| Evidence ID | Evidence area | Required artifacts | Acceptance threshold | Owner | Reviewers | Review cadence | Status |
|---|---|---|---|---|---|---|---|
| `P5-EVID-001` | host_test_regression | `pytest_tests.log`, `pytest_tests_junit.xml` | `pytest tests/` passes with zero unexpected failures and zero skipped critical groups. | QA owner | Release lead, host maintainer | Per release candidate | `not_started` |
| `P5-EVID-002` | bench_timing_regression | `pytest_bench.log`, `bench_summary.json` | `pytest bench/` passes and recorded timing checks remain within existing approved envelopes. | Bench owner | Release lead, timing reviewer | Per release candidate | `not_started` |
| `P5-EVID-003` | firmware_unit_validation | `run_tests.log`, `firmware_summary.txt` | `run_tests.bat` passes on supported platforms with no failing unit groups. | Firmware owner | Release lead, firmware maintainer | Per release candidate | `not_started` |
| `P5-EVID-004` | coverage_snapshot | `coverage.log`, `coverage.xml` | `pytest --cov=src/coloursorter --cov-report=xml` completes and publishes `coverage.xml` for review. | QA owner | Release lead, host maintainer | Weekly while open | `not_started` |
| `P5-EVID-005` | long_run_parity_campaign | `campaign_manifest.json`, `campaign_summary.json`, `parity_review.md` | Phase 5 long-run parity campaign records zero divergences, zero missing terminal records, and zero trace-hash mismatches. | Validation owner | Release lead, bench owner | Weekly while open | `not_started` |
| `P5-EVID-006` | release_packet_review | `release_checklist.md`, `approval_record.md` | Every evidence row is approved, all blockers are closed or waived in writing, and release sign-off is recorded. | Release lead | QA owner, firmware owner, bench owner | Per release candidate | `not_started` |

## Artifact contract

Each populated matrix row must declare the following fields without omission:

- `evidence_id`
- `evidence_area`
- `artifact_paths`
- `command_reference`
- `acceptance_threshold`
- `owner`
- `reviewers`
- `review_cadence`
- `status`
- `last_reviewed_utc`
- `blocking_issues`

## Ownership model

| Role | Responsibility |
|---|---|
| Release lead | Maintains the active matrix, confirms row completion order, and records final sign-off. |
| QA owner | Verifies host tests and coverage evidence artifacts are present and reproducible. |
| Bench owner | Verifies bench timing and long-run parity evidence remain deterministic and within existing envelopes. |
| Firmware owner | Verifies firmware unit evidence on supported execution platforms. |
| Validation owner | Confirms parity-review completeness and trace artifact integrity. |

## Review cadence rules

1. Open a fresh matrix for each release candidate using the stable `matrix_id` plus release-candidate suffix.
2. Review every row at least once per release candidate.
3. Re-review rows `P5-EVID-004` and `P5-EVID-005` weekly while the release candidate remains open.
4. Any row marked `blocked` must include a written blocker summary and next review date.
5. Final release approval is forbidden until all rows are `approved`.

## Suggested storage layout

```text
docs/artifacts/phase5/release_evidence/
  RC-<nnn>/
    release_evidence_matrix.md
    P5-EVID-001/
      pytest_tests.log
      pytest_tests_junit.xml
    P5-EVID-002/
      pytest_bench.log
      bench_summary.json
    P5-EVID-003/
      run_tests.log
      firmware_summary.txt
    P5-EVID-004/
      coverage.log
      coverage.xml
    P5-EVID-005/
      campaign_manifest.json
      campaign_summary.json
      parity_review.md
    P5-EVID-006/
      release_checklist.md
      approval_record.md
```

## Release review checklist

- [ ] All six canonical evidence rows are present.
- [ ] All required artifacts exist under the canonical storage root.
- [ ] All acceptance thresholds are satisfied without redefining frozen contracts.
- [ ] Each row has an assigned owner and named reviewers.
- [ ] Review cadence entries are populated and current.
- [ ] Final release sign-off is recorded by the release lead.

## Non-goals

- No runtime code changes.
- No protocol or schema changes.
- No new timing thresholds beyond already approved envelopes.
- No nondeterministic evidence naming or storage.
