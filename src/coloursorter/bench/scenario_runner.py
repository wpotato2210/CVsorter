from __future__ import annotations

import argparse
import sys

from .scenarios import BenchScenario, BenchSummary, default_scenarios


def _resolve_scenarios(selected_name: str | None) -> tuple[BenchScenario, ...]:
    scenarios = default_scenarios()
    if selected_name is None:
        return scenarios
    for scenario in scenarios:
        if scenario.name == selected_name:
            return (scenario,)
    available = ", ".join(scenario.name for scenario in scenarios)
    raise ValueError(f"Unknown scenario '{selected_name}'. Available: {available}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate ColourSorter bench scenarios")
    parser.add_argument("--scenario", type=str, default=None, help="Scenario name (default: evaluate all)")
    parser.add_argument("--avg-rtt-ms", type=float, required=True)
    parser.add_argument("--peak-rtt-ms", type=float, required=True)
    parser.add_argument("--safe-transitions", type=int, default=0)
    parser.add_argument("--watchdog-transitions", type=int, default=0)
    parser.add_argument("--recovered-from-safe", action="store_true")
    args = parser.parse_args(argv)

    if args.scenario is None and args.safe_transitions == 0 and not args.recovered_from_safe:
        print(
            "Hint: in all-scenario mode, fault_to_safe requires --safe-transitions > 0; "
            "recovery_flow requires --safe-transitions > 0 and --recovered-from-safe.",
            file=sys.stderr,
        )

    summary = BenchSummary(
        avg_round_trip_ms=args.avg_rtt_ms,
        max_round_trip_ms=args.peak_rtt_ms,
        safe_transitions=args.safe_transitions,
        watchdog_transitions=args.watchdog_transitions,
        recovered_from_safe=args.recovered_from_safe,
    )

    scenarios = _resolve_scenarios(args.scenario)
    results = tuple(scenario.evaluate(summary) for scenario in scenarios)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
