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
        "informational_only": False,
        "rerun_consistent": rerun_consistent,
        "deterministic_fingerprint": "|".join(sorted(normalized_rows)),
    }


def _evaluate_release_gate(payload: dict[str, Any], summary: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    runs = payload["runs"]

    if payload.get("vector_pack") != "T3-004":
        failures.append("vector_pack must be T3-004")

    if payload.get("seed") != 3004:
        failures.append("seed must be deterministic value 3004")

    if not runs:
        failures.append("runs must be non-empty")

    expected_statuses = sorted({str(run["expected_status"]) for run in runs})
    if expected_statuses != ["informational_pass"]:
        failures.append("expected_status entries must all be informational_pass")

    inconsistent_scenarios = [
        scenario_id
        for scenario_id, consistent in summary["rerun_consistent"].items()
        if not consistent
    ]
    if inconsistent_scenarios:
        failures.append(
            "rerun consistency failed for scenarios: " + ", ".join(inconsistent_scenarios)
        )

    return len(failures) == 0, failures


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
    passed, failures = _evaluate_release_gate(payload, summary)
    report = {
        **summary,
        "gate_passed": passed,
        "gate_failures": failures,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
