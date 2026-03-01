from __future__ import annotations

from coloursorter.bench import scenarios_from_thresholds
from coloursorter.config import ScenarioThresholdsConfig


def test_scenarios_from_thresholds_uses_runtime_values() -> None:
    thresholds = ScenarioThresholdsConfig(
        nominal_max_avg_rtt_ms=9.0,
        nominal_max_peak_rtt_ms=14.0,
        stress_max_avg_rtt_ms=20.0,
        stress_max_peak_rtt_ms=50.0,
        fault_max_avg_rtt_ms=33.0,
        fault_max_peak_rtt_ms=70.0,
    )

    scenarios = {scenario.name: scenario for scenario in scenarios_from_thresholds(thresholds)}

    assert scenarios["nominal"].max_avg_rtt_ms == 9.0
    assert scenarios["nominal"].max_peak_rtt_ms == 14.0
    assert scenarios["latency_stress"].max_avg_rtt_ms == 20.0
    assert scenarios["fault_to_safe"].max_peak_rtt_ms == 70.0
    assert scenarios["recovery_flow"].max_avg_rtt_ms == 33.0
