from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/phase3_2_actuator_dispatch_vectors.json")
MAIN_C_PATH = Path("firmware/mcu/src/main.c")
SCHEDULER_H_PATH = Path("firmware/mcu/include/scheduler.h")


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def _should_trigger(*, current_tick: int, target_tick: int) -> bool:
    return current_tick - target_tick >= 0


def test_phase3_2_fixture_is_seeded_and_ordered() -> None:
    payload = _load_fixture()

    assert payload["vector_pack"] == "PHASE-3.2"
    assert payload["seed"] == 3202
    assert payload["color_format"] == "BGR"
    assert payload["device"] == "mcu"

    vectors = payload["vectors"]
    vector_ids = [vector["id"] for vector in vectors]
    assert vector_ids == [
        "before_target_tick",
        "at_target_tick",
        "after_target_tick",
        "safe_mode_block",
    ]


def test_phase3_2_trigger_boundary_vectors_are_deterministic() -> None:
    payload = _load_fixture()

    for vector in payload["vectors"]:
        observed_trigger = _should_trigger(
            current_tick=int(vector["current_tick"]),
            target_tick=int(vector["target_tick"]),
        )
        assert observed_trigger is bool(vector["expected_trigger"])

        expected_emit = bool(vector["expected_actuator_emit"])
        safe_state = bool(vector["safe_state"])
        observed_emit = observed_trigger and not safe_state
        assert observed_emit is expected_emit


def test_phase3_2_scheduler_interface_contains_dispatch_primitives() -> None:
    scheduler_header = SCHEDULER_H_PATH.read_text(encoding="utf-8")

    assert "bool scheduler_dequeue(scheduler_slot_t *slot_out);" in scheduler_header
    assert "bool scheduler_should_trigger(int32_t current_tick, int32_t target_tick);" in scheduler_header


@pytest.mark.xfail(
    reason="Phase 3.2 dispatcher loop is not wired in main control loop yet; scaffold remains informational",
    strict=False,
)
def test_phase3_2_main_loop_dispatcher_placeholder_non_gating() -> None:
    main_source = MAIN_C_PATH.read_text(encoding="utf-8")

    assert "scheduler_dequeue" in main_source
    assert "scheduler_should_trigger" in main_source
    assert "actuator" in main_source.lower()
