from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.config.pipeline_config import DEFAULT_PIPELINE_CONFIG, RuntimeTimingSample
from coloursorter.scheduler.scheduler import schedule_actuation


FIXTURE_PATH = Path("tests/fixtures/phase3_2_actuator_dispatch_vectors.json")
SCHEDULER_SOURCE_PATH = Path("src/coloursorter/scheduler/scheduler.py")
RUNTIME_CONFIG_PATH = Path("src/coloursorter/config/pipeline_config.py")



def _load_vectors() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise AssertionError("phase3.2 vectors must be a non-empty list")
    return vectors


def test_phase3_2_fixture_pack_and_contract_order_are_stable() -> None:
    vectors = _load_vectors()
    vector_ids = [str(vector["id"]) for vector in vectors]

    assert vector_ids == [
        "before_target_tick",
        "at_target_tick",
        "after_target_tick",
        "safe_mode_block",
    ]


def test_phase3_2_runtime_timing_variables_are_declared_in_config_package() -> None:
    source = RUNTIME_CONFIG_PATH.read_text(encoding="utf-8")

    for required in (
        "frame_timestamp_ms",
        "pipeline_latency_ms",
        "trigger_offset_ms",
        "actuation_delay_ms",
    ):
        assert required in source


def test_phase3_2_scheduler_uses_runtime_timing_sample_without_inline_physical_constants() -> None:
    sample = RuntimeTimingSample(
        frame_timestamp_ms=1000,
        pipeline_latency_ms=6,
        trigger_offset_ms=12,
        actuation_delay_ms=8,
    )

    scheduled = schedule_actuation(lane=2, timing=sample, config=DEFAULT_PIPELINE_CONFIG)
    assert scheduled.execute_at_ms == 1020

    repeat = schedule_actuation(lane=2, timing=sample, config=DEFAULT_PIPELINE_CONFIG)
    assert repeat == scheduled


def test_phase3_2_scheduler_negative_timing_values_raise() -> None:
    with pytest.raises(ValueError, match="frame_timestamp_ms"):
        schedule_actuation(
            lane=0,
            timing=RuntimeTimingSample(
                frame_timestamp_ms=-1,
                pipeline_latency_ms=0,
                trigger_offset_ms=0,
                actuation_delay_ms=0,
            ),
            config=DEFAULT_PIPELINE_CONFIG,
        )


def test_phase3_2_scheduler_contract_includes_trigger_offset_and_actuation_delay() -> None:
    scheduler_source = SCHEDULER_SOURCE_PATH.read_text(encoding="utf-8")
    assert "execute_at_ms = timing.frame_timestamp_ms + timing.trigger_offset_ms + timing.actuation_delay_ms" in scheduler_source
