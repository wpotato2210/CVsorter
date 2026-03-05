from __future__ import annotations

from coloursorter.deploy.logging import to_canonical_timing_diagnostics


def test_to_canonical_timing_diagnostics_uses_explicit_trigger_offset() -> None:
    timing = to_canonical_timing_diagnostics(
        frame_timestamp_ms=1234.0,
        ingest_latency_ms=1.0,
        decision_latency_ms=2.0,
        schedule_latency_ms=3.0,
        transport_latency_ms=4.0,
        cycle_latency_ms=20.0,
        trigger_offset_ms=7.5,
    )

    assert timing.frame_timestamp_ms == 1234.0
    assert timing.pipeline_latency_ms == 6.0
    assert timing.trigger_offset_ms == 7.5
    assert timing.actuation_delay_ms == 4.0


def test_to_canonical_timing_diagnostics_falls_back_to_cycle_derived_trigger_offset() -> None:
    timing = to_canonical_timing_diagnostics(
        frame_timestamp_ms=1000.0,
        ingest_latency_ms=2.0,
        decision_latency_ms=4.0,
        schedule_latency_ms=6.0,
        transport_latency_ms=5.0,
        cycle_latency_ms=40.0,
        trigger_offset_ms=None,
    )

    # fallback = max(0, cycle - pipeline - transport) = max(0, 40 - 12 - 5) = 23
    assert timing.trigger_offset_ms == 23.0
