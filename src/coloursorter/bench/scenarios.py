from __future__ import annotations

from dataclasses import dataclass

from coloursorter.config import ScenarioThresholdsConfig


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
    reject_reliability: float = 1.0
    max_jitter_ms: float = 0.0
    missed_window_count: int = 0


@dataclass(frozen=True)
class BenchScenario:
    name: str
    max_avg_rtt_ms: float
    max_peak_rtt_ms: float
    require_safe_transition: bool
    require_recovery: bool
    min_reject_reliability: float = 0.0
    max_jitter_ms: float = float("inf")
    max_missed_window_count: int = 1_000_000

    def evaluate(self, summary: BenchSummary) -> ScenarioResult:
        checks = [
            summary.avg_round_trip_ms <= self.max_avg_rtt_ms,
            summary.max_round_trip_ms <= self.max_peak_rtt_ms,
            (not self.require_safe_transition) or summary.safe_transitions > 0,
            (not self.require_recovery) or summary.recovered_from_safe,
            summary.reject_reliability >= self.min_reject_reliability,
            summary.max_jitter_ms <= self.max_jitter_ms,
            summary.missed_window_count <= self.max_missed_window_count,
        ]
        return ScenarioResult(
            name=self.name,
            passed=all(checks),
            detail=(
                f"avg_rtt={summary.avg_round_trip_ms:.2f}ms, "
                f"peak_rtt={summary.max_round_trip_ms:.2f}ms, "
                f"safe={summary.safe_transitions}, watchdog={summary.watchdog_transitions}, "
                f"recovered={summary.recovered_from_safe}, reject_reliability={summary.reject_reliability:.3f}, "
                f"max_jitter={summary.max_jitter_ms:.2f}ms, missed_windows={summary.missed_window_count}"
            ),
        )


def scenarios_from_thresholds(thresholds: ScenarioThresholdsConfig) -> tuple[BenchScenario, ...]:
    return (
        BenchScenario(
            "nominal",
            max_avg_rtt_ms=thresholds.nominal_max_avg_rtt_ms,
            max_peak_rtt_ms=thresholds.nominal_max_peak_rtt_ms,
            require_safe_transition=False,
            require_recovery=False,
            min_reject_reliability=0.99,
            max_jitter_ms=10.0,
            max_missed_window_count=0,
        ),
        BenchScenario(
            "latency_stress",
            max_avg_rtt_ms=thresholds.stress_max_avg_rtt_ms,
            max_peak_rtt_ms=thresholds.stress_max_peak_rtt_ms,
            require_safe_transition=False,
            require_recovery=False,
            min_reject_reliability=0.99,
            max_jitter_ms=10.0,
            max_missed_window_count=0,
        ),
        BenchScenario(
            "fault_to_safe",
            max_avg_rtt_ms=thresholds.fault_max_avg_rtt_ms,
            max_peak_rtt_ms=thresholds.fault_max_peak_rtt_ms,
            require_safe_transition=True,
            require_recovery=False,
            min_reject_reliability=0.99,
            max_jitter_ms=10.0,
            max_missed_window_count=0,
        ),
        BenchScenario(
            "recovery_flow",
            max_avg_rtt_ms=thresholds.fault_max_avg_rtt_ms,
            max_peak_rtt_ms=thresholds.fault_max_peak_rtt_ms,
            require_safe_transition=True,
            require_recovery=True,
            min_reject_reliability=0.99,
            max_jitter_ms=10.0,
            max_missed_window_count=0,
        ),
    )


def default_scenarios() -> tuple[BenchScenario, ...]:
    return (
        BenchScenario("nominal", max_avg_rtt_ms=12.0, max_peak_rtt_ms=25.0, require_safe_transition=False, require_recovery=False, min_reject_reliability=0.99, max_jitter_ms=10.0, max_missed_window_count=0),
        BenchScenario("latency_stress", max_avg_rtt_ms=25.0, max_peak_rtt_ms=60.0, require_safe_transition=False, require_recovery=False, min_reject_reliability=0.99, max_jitter_ms=10.0, max_missed_window_count=0),
        BenchScenario("fault_to_safe", max_avg_rtt_ms=40.0, max_peak_rtt_ms=80.0, require_safe_transition=True, require_recovery=False, min_reject_reliability=0.99, max_jitter_ms=10.0, max_missed_window_count=0),
        BenchScenario("recovery_flow", max_avg_rtt_ms=40.0, max_peak_rtt_ms=80.0, require_safe_transition=True, require_recovery=True, min_reject_reliability=0.99, max_jitter_ms=10.0, max_missed_window_count=0),
    )
