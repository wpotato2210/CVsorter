from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class BenchSummary:
    avg_round_trip_ms: float
    max_round_trip_ms: float
    safe_transitions: int
    watchdog_transitions: int
    recovered_from_safe: bool


@dataclass(frozen=True)
class BenchScenario:
    name: str
    max_avg_rtt_ms: float
    max_peak_rtt_ms: float
    require_safe_transition: bool
    require_recovery: bool

    def evaluate(self, summary: BenchSummary) -> ScenarioResult:
        checks = [
            summary.avg_round_trip_ms <= self.max_avg_rtt_ms,
            summary.max_round_trip_ms <= self.max_peak_rtt_ms,
            (not self.require_safe_transition) or summary.safe_transitions > 0,
            (not self.require_recovery) or summary.recovered_from_safe,
        ]
        return ScenarioResult(
            name=self.name,
            passed=all(checks),
            detail=(
                f"avg_rtt={summary.avg_round_trip_ms:.2f}ms, "
                f"peak_rtt={summary.max_round_trip_ms:.2f}ms, "
                f"safe={summary.safe_transitions}, watchdog={summary.watchdog_transitions}, "
                f"recovered={summary.recovered_from_safe}"
            ),
        )


def default_scenarios() -> tuple[BenchScenario, ...]:
    return (
        BenchScenario("nominal", max_avg_rtt_ms=12.0, max_peak_rtt_ms=25.0, require_safe_transition=False, require_recovery=False),
        BenchScenario("latency_stress", max_avg_rtt_ms=25.0, max_peak_rtt_ms=60.0, require_safe_transition=False, require_recovery=False),
        BenchScenario("fault_to_safe", max_avg_rtt_ms=40.0, max_peak_rtt_ms=80.0, require_safe_transition=True, require_recovery=False),
        BenchScenario("recovery_flow", max_avg_rtt_ms=40.0, max_peak_rtt_ms=80.0, require_safe_transition=True, require_recovery=True),
    )
