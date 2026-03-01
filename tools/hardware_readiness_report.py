#!/usr/bin/env python3
"""Summarize hardware readiness gate status from checked-in artifacts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class GateCriterion:
    name: str
    required_artifacts: tuple[Path, ...]


CRITERIA: tuple[GateCriterion, ...] = (
    GateCriterion(
        name="Protocol interoperability",
        required_artifacts=(
            Path("docs/artifacts/hardware_readiness/protocol/bench_protocol_trace.log"),
            Path("docs/artifacts/hardware_readiness/protocol/hardware_protocol_trace.log"),
            Path("docs/artifacts/hardware_readiness/protocol/protocol_interop_summary.md"),
        ),
    ),
    GateCriterion(
        name="Queue behavior",
        required_artifacts=(
            Path("docs/artifacts/hardware_readiness/queue/bench_queue_stress.log"),
            Path("docs/artifacts/hardware_readiness/queue/hardware_queue_stress.log"),
            Path("docs/artifacts/hardware_readiness/queue/queue_behavior_summary.md"),
        ),
    ),
    GateCriterion(
        name="SAFE/watchdog recovery",
        required_artifacts=(
            Path("docs/artifacts/hardware_readiness/safety/bench_fault_injection.log"),
            Path("docs/artifacts/hardware_readiness/safety/hardware_fault_injection.log"),
            Path("docs/artifacts/hardware_readiness/safety/safe_watchdog_recovery_summary.md"),
        ),
    ),
    GateCriterion(
        name="Timing budget conformance",
        required_artifacts=(
            Path("docs/artifacts/hardware_readiness/timing/bench_timing_budget.csv"),
            Path("docs/artifacts/hardware_readiness/timing/hardware_timing_budget.csv"),
            Path("docs/artifacts/hardware_readiness/timing/timing_budget_summary.md"),
        ),
    ),
)


def _is_present(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _missing_paths(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if not _is_present(path)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless all criteria pass.",
    )
    args = parser.parse_args()

    all_pass = True
    print("Hardware Readiness Gate Summary")
    print("=" * 32)

    for criterion in CRITERIA:
        missing = _missing_paths(criterion.required_artifacts)
        status = "PASS" if not missing else "FAIL"
        all_pass = all_pass and not missing

        print(f"- {criterion.name}: {status}")
        if missing:
            for missing_path in missing:
                print(f"    missing: {missing_path}")

    print("\nOverall status:", "PASS" if all_pass else "FAIL")

    if args.strict and not all_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
