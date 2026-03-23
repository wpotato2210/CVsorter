from __future__ import annotations

from pathlib import Path


SPEC_PATH = Path("docs/phase5_long_run_campaign_spec.md")


def _read_spec() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def test_t5_003_spec_exists_and_declares_planning_only_status() -> None:
    spec = _read_spec()

    assert SPEC_PATH.exists()
    assert "# Phase 5 Long-Run Parity Campaign Specification (T5-003)" in spec
    assert "Status: Draft (planning only; no runtime, protocol, schema, or OpenSpec contract changes)." in spec


def test_t5_003_spec_declares_required_campaign_constants() -> None:
    spec = _read_spec()

    required_rows = (
        "| `campaign_id` | `P5-LONG-RUN-PARITY-001` | Stable campaign identifier. |",
        "| `session_count` | 12 | Total required sessions per execution window. |",
        "| `sessions_per_fixture` | 3 | Repeats per fixture. |",
        "| `fixture_count` | 4 | Fixed fixture pack cardinality. |",
        "| `bench_seed_base` | 500300 | Base seed for bench sessions. |",
        "| `live_seed_base` | 500600 | Base seed for live sessions. |",
        "| `max_allowed_divergences` | 0 | No parity divergence is acceptable. |",
        "| `artifact_root` | `docs/artifacts/phase5/long_run_parity/` | Canonical artifact storage path. |",
    )

    for row in required_rows:
        assert row in spec


def test_t5_003_spec_freezes_fixture_pack_and_session_matrix() -> None:
    spec = _read_spec()

    expected_fixtures = (
        "1. `protocol_vectors_t3_001`",
        "2. `timing_jitter_t3_002`",
        "3. `trigger_correlation_t3_003`",
        "4. `bench_live_parity_t3_005`",
    )
    for fixture in expected_fixtures:
        assert fixture in spec

    expected_sessions = (
        "| `P5-LRP-001` | `protocol_vectors_t3_001` | `bench` | 500301 |",
        "| `P5-LRP-002` | `protocol_vectors_t3_001` | `live` | 500601 |",
        "| `P5-LRP-012` | `bench_live_parity_t3_005` | `bench` | 500308 |",
    )
    for session in expected_sessions:
        assert session in spec

    assert spec.count("| `P5-LRP-") == 12


def test_t5_003_spec_declares_acceptance_metrics_and_storage_contract() -> None:
    spec = _read_spec()

    expected_metrics = (
        "1. **Parity decision stability:** `decision`, `reason`, `mode`, `queue_depth`, and `scheduler_state` remain identical for paired bench/live sessions.",
        "2. **Terminal trace completeness:** each accepted command maps to exactly one terminal status record.",
        "3. **Deterministic replay stability:** repeated sessions for the same fixture and environment produce identical trace hashes.",
        "4. **Timing envelope conformance:** all replayed sessions remain within the existing Phase 3 and Phase 4 timing envelopes; no new timing thresholds are introduced here.",
        "5. **Artifact completeness:** each session writes the required manifest, summary, trace, and hash outputs into the canonical storage path.",
    )
    for metric in expected_metrics:
        assert metric in spec

    expected_storage_entries = (
        "- `manifest.json`",
        "- `summary.json`",
        "- `trace.log`",
        "- `trace.sha256`",
        "docs/artifacts/phase5/long_run_parity/",
        "campaign_manifest.json",
    )
    for entry in expected_storage_entries:
        assert entry in spec
