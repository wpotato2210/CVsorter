from __future__ import annotations

from pathlib import Path


MAIN_C_PATH = Path("firmware/mcu/src/main.c")
SCHEDULER_C_PATH = Path("firmware/mcu/src/scheduler.c")
SCHEDULER_H_PATH = Path("firmware/mcu/include/scheduler.h")
ACTUATOR_H_PATH = Path("firmware/mcu/include/actuator.h")
ACTUATOR_C_PATH = Path("firmware/mcu/src/actuator.c")
FIRMWARE_CONFIG_PATH = Path("firmware/mcu/config/firmware_config.h")


def test_phase3_2_dispatch_result_contracts_defined() -> None:
    scheduler_header = SCHEDULER_H_PATH.read_text(encoding="utf-8")

    assert "DISPATCH_RESULT_EXECUTED" in scheduler_header
    assert "DISPATCH_RESULT_MISSED_WINDOW" in scheduler_header
    assert "DISPATCH_RESULT_SAFE_BLOCKED" in scheduler_header
    assert "dispatch_result_t scheduler_dispatch_ready_slot(int32_t current_tick, uint8_t *lane_out);" in scheduler_header


def test_phase3_2_main_loop_invokes_dispatcher_and_actuator() -> None:
    main_source = MAIN_C_PATH.read_text(encoding="utf-8")

    assert "actuator_init();" in main_source
    assert "scheduler_dispatch_ready_slot" in main_source
    assert "actuator_emit_pulse" in main_source
    assert "FW_ACTUATION_PULSE_WIDTH_MS" in main_source


def test_phase3_2_actuator_interface_is_explicit() -> None:
    actuator_header = ACTUATOR_H_PATH.read_text(encoding="utf-8")
    actuator_source = ACTUATOR_C_PATH.read_text(encoding="utf-8")

    assert "void actuator_emit_pulse(uint8_t lane, uint16_t pulse_width_ms);" in actuator_header
    assert "bool actuator_last_command(uint8_t *lane_out, uint16_t *pulse_width_ms_out);" in actuator_header
    assert "s_last_pulse_width_ms" in actuator_source


def test_phase3_2_dispatch_uses_safe_and_miss_window_guards() -> None:
    scheduler_source = SCHEDULER_C_PATH.read_text(encoding="utf-8")

    assert "if (scheduler_safe_state())" in scheduler_source
    assert "FW_DISPATCH_MISS_TICKS" in scheduler_source
    assert "queue_peek" in scheduler_source
    assert "queue_pop" in scheduler_source


def test_phase3_2_physical_timing_constants_are_in_config() -> None:
    firmware_config = FIRMWARE_CONFIG_PATH.read_text(encoding="utf-8")

    assert "#define FW_ACTUATION_PULSE_WIDTH_MS" in firmware_config
    assert "#define FW_DISPATCH_MISS_TICKS" in firmware_config
