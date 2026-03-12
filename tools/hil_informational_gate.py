from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise ValueError("fixture 'runs' must be a list")
    return payload


def _build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload["runs"]
    grouped_hashes: dict[str, list[str]] = defaultdict(list)

    normalized_rows: list[str] = []
    for run in runs:
        scenario_id = str(run["scenario_id"])
        trace_hash = str(run["trace_hash"])
        expected_status = str(run["expected_status"])
        grouped_hashes[scenario_id].append(trace_hash)
        normalized_rows.append(f"{scenario_id}:{trace_hash}:{expected_status}")

    rerun_consistent = {
        scenario_id: len(set(trace_hashes)) == 1
        for scenario_id, trace_hashes in sorted(grouped_hashes.items())
    }

    return {
        "vector_pack": payload.get("vector_pack"),
        "seed": payload.get("seed"),
        "informational_only": True,
        "rerun_consistent": rerun_consistent,
        "deterministic_fingerprint": "|".join(sorted(normalized_rows)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T3-004 deterministic HIL gate scaffold (informational mode only)."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("tests/fixtures/hil_gate_t3_004.json"),
        help="Path to deterministic HIL fixture.",
    )
    args = parser.parse_args()

    payload = _load_fixture(args.fixture)
    summary = _build_summary(payload)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
