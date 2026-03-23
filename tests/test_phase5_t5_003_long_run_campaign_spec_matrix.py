from __future__ import annotations

import re
from pathlib import Path


SPEC_PATH = Path("docs/phase5_long_run_campaign_spec.md")
SESSION_ROW_PATTERN = re.compile(
    r"\| `(?P<session_id>P5-LRP-\d{3})` \| `(?P<fixture>[^`]+)` \| `(?P<environment>bench|live)` \| (?P<seed>\d+) \|"
)


def _read_spec() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def _session_rows() -> list[dict[str, str]]:
    return [match.groupdict() for match in SESSION_ROW_PATTERN.finditer(_read_spec())]


def test_t5_003_session_matrix_is_complete_and_deterministically_ordered() -> None:
    rows = _session_rows()

    assert [row["session_id"] for row in rows] == [f"P5-LRP-{index:03d}" for index in range(1, 13)]
    assert [row["fixture"] for row in rows] == [
        "protocol_vectors_t3_001",
        "protocol_vectors_t3_001",
        "protocol_vectors_t3_001",
        "timing_jitter_t3_002",
        "timing_jitter_t3_002",
        "timing_jitter_t3_002",
        "trigger_correlation_t3_003",
        "trigger_correlation_t3_003",
        "trigger_correlation_t3_003",
        "bench_live_parity_t3_005",
        "bench_live_parity_t3_005",
        "bench_live_parity_t3_005",
    ]
    assert [row["environment"] for row in rows] == [
        "bench",
        "live",
        "bench",
        "bench",
        "live",
        "bench",
        "bench",
        "live",
        "bench",
        "bench",
        "live",
        "bench",
    ]


def test_t5_003_session_matrix_seeds_match_declared_bases_and_fixture_repeats() -> None:
    spec = _read_spec()
    rows = _session_rows()

    assert "| `bench_seed_base` | 500300 | Base seed for bench sessions. |" in spec
    assert "| `live_seed_base` | 500600 | Base seed for live sessions. |" in spec

    bench_seeds = [int(row["seed"]) for row in rows if row["environment"] == "bench"]
    live_seeds = [int(row["seed"]) for row in rows if row["environment"] == "live"]

    assert bench_seeds == [500301, 500302, 500303, 500304, 500305, 500306, 500307, 500308]
    assert live_seeds == [500601, 500602, 500603, 500604]

    fixture_counts: dict[str, int] = {}
    for row in rows:
        fixture_counts[row["fixture"]] = fixture_counts.get(row["fixture"], 0) + 1

    assert fixture_counts == {
        "protocol_vectors_t3_001": 3,
        "timing_jitter_t3_002": 3,
        "trigger_correlation_t3_003": 3,
        "bench_live_parity_t3_005": 3,
    }
