from __future__ import annotations

from pathlib import Path


SPEC_PATH = Path("docs/phase5_release_evidence_matrix.md")


def _read_spec() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def test_t5_001_spec_exists_and_declares_planning_only_status() -> None:
    spec = _read_spec()

    assert SPEC_PATH.exists()
    assert "# Phase 5 Release Evidence Matrix Template (T5-001)" in spec
    assert "Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes)." in spec


def test_t5_001_spec_declares_required_template_constants() -> None:
    spec = _read_spec()

    required_rows = (
        "| `matrix_id` | `P5-REL-EVIDENCE-001` | Stable matrix identifier for release governance records. |",
        "| `artifact_root` | `docs/artifacts/phase5/release_evidence/` | Canonical evidence storage root. |",
        "| `minimum_required_rows` | 6 | Every release packet must populate all canonical evidence rows. |",
        "| `max_missing_artifacts` | 0 | No required artifact may be absent at review time. |",
        "| `max_unapproved_rows` | 0 | All rows require explicit owner approval before release sign-off. |",
        "| `review_cadence` | `per release candidate + weekly while open` | Mandatory governance review timing. |",
    )

    for row in required_rows:
        assert row in spec


def test_t5_001_spec_freezes_canonical_evidence_rows_and_thresholds() -> None:
    spec = _read_spec()

    expected_rows = (
        "| `P5-EVID-001` | host_test_regression | `pytest_tests.log`, `pytest_tests_junit.xml` | `pytest tests/` passes with zero unexpected failures and zero skipped critical groups. | QA owner | Release lead, host maintainer | Per release candidate | `not_started` |",
        "| `P5-EVID-004` | coverage_snapshot | `coverage.log`, `coverage.xml` | `pytest --cov=src/coloursorter --cov-report=xml` completes and publishes `coverage.xml` for review. | QA owner | Release lead, host maintainer | Weekly while open | `not_started` |",
        "| `P5-EVID-005` | long_run_parity_campaign | `campaign_manifest.json`, `campaign_summary.json`, `parity_review.md` | Phase 5 long-run parity campaign records zero divergences, zero missing terminal records, and zero trace-hash mismatches. | Validation owner | Release lead, bench owner | Weekly while open | `not_started` |",
        "| `P5-EVID-006` | release_packet_review | `release_checklist.md`, `approval_record.md` | Every evidence row is approved, all blockers are closed or waived in writing, and release sign-off is recorded. | Release lead | QA owner, firmware owner, bench owner | Per release candidate | `not_started` |",
    )
    for row in expected_rows:
        assert row in spec

    assert spec.count("| `P5-EVID-00") == 6


def test_t5_001_spec_declares_artifact_contract_ownership_and_review_rules() -> None:
    spec = _read_spec()

    required_fields = (
        "- `evidence_id`",
        "- `evidence_area`",
        "- `artifact_paths`",
        "- `command_reference`",
        "- `acceptance_threshold`",
        "- `owner`",
        "- `reviewers`",
        "- `review_cadence`",
        "- `status`",
        "- `last_reviewed_utc`",
        "- `blocking_issues`",
        "| Release lead | Maintains the active matrix, confirms row completion order, and records final sign-off. |",
        "| Bench owner | Verifies bench timing and long-run parity evidence remain deterministic and within existing envelopes. |",
        "1. Open a fresh matrix for each release candidate using the stable `matrix_id` plus release-candidate suffix.",
        "3. Re-review rows `P5-EVID-004` and `P5-EVID-005` weekly while the release candidate remains open.",
        "5. Final release approval is forbidden until all rows are `approved`.",
        "docs/artifacts/phase5/release_evidence/",
        "release_evidence_matrix.md",
    )
    for item in required_fields:
        assert item in spec
