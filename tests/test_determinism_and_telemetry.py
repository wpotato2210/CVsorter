from __future__ import annotations

from pathlib import Path
import time

from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig
from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.types import FaultState
from coloursorter.bench.virtual_encoder import EncoderConfig, EncoderFaultConfig, VirtualEncoder
from coloursorter.deploy import PipelineRunner
from coloursorter.model import ObjectDetection

FIXTURES = Path(__file__).parent / "fixtures"


def _build_pipeline() -> PipelineRunner:
    return PipelineRunner(
        lane_config_path=FIXTURES / "lane_geometry_22.yaml",
        calibration_path=FIXTURES / "calibration_edge_valid.json",
    )


def _reject_detection() -> ObjectDetection:
    return ObjectDetection(
        object_id="det-1",
        centroid_x_px=120.0,
        centroid_y_px=240.0,
        classification="reject",
    )


def test_encoder_accumulator_preserves_low_speed_pulses_deterministically() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=10.0, pulley_circumference_mm=200.0)
    )
    pulses = [encoder.pulses_between(i * 0.1, (i + 1) * 0.1) for i in range(10)]
    assert sum(pulses) == 5
    assert pulses.count(0) > 0


def test_zero_speed_and_missing_pulse_faults_are_deterministic() -> None:
    zero_speed = VirtualEncoder(
        EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0),
        fault_config=EncoderFaultConfig(force_zero_speed=True),
    )
    missing = VirtualEncoder(
        EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0),
        fault_config=EncoderFaultConfig(force_missing_pulses=True),
    )
    assert zero_speed.pulses_between(0.0, 1.0) == 0
    assert missing.pulses_between(0.0, 1.0) == 0


def test_bench_logs_include_required_telemetry_fields() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    logs = runner.run_cycle(
        frame_id=1,
        timestamp_s=0.2,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=0.1,
    )
    assert logs
    log = logs[0]
    assert log.frame_timestamp_s > 0
    assert log.trigger_timestamp_s >= 0
    assert log.trigger_timestamp_s > log.trigger_generation_s
    assert log.trigger_mm > 0
    assert log.lane_index >= 0
    assert log.rejection_reason is not None
    assert log.belt_speed_mm_s > 0
    assert log.queue_depth >= 0
    assert log.scheduler_state
    assert log.mode
    assert log.command_source == "auto_pipeline"


def test_trigger_timestamp_uses_distance_and_stage_timing_projection() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    log = runner.run_cycle(
        frame_id=1,
        timestamp_s=0.2,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=0.1,
    )[0]

    minimum_projection_s = log.trigger_generation_s + (log.trigger_mm / log.belt_speed_mm_s)
    assert log.trigger_timestamp_s >= minimum_projection_s
    assert log.trigger_timestamp_s >= log.trigger_generation_s + ((log.decision_latency_ms + log.schedule_latency_ms) / 1000.0)


def test_trigger_timestamp_is_anchored_to_last_encoder_pulse_across_dropout_cycles() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(
            EncoderConfig(
                pulses_per_revolution=100,
                belt_speed_mm_per_s=100.0,
                pulley_circumference_mm=200.0,
                dropout_ratio=0.95,
            )
        ),
    )

    first = runner.run_cycle(1, 0.2, 720, 1056, [_reject_detection()], 0.1)[0]
    second = runner.run_cycle(2, 0.3, 720, 1056, [_reject_detection()], 0.2)[0]

    assert first.trigger_generation_s == 0.1
    assert second.trigger_generation_s == 0.2
    assert second.trigger_generation_s >= first.trigger_generation_s
    assert second.trigger_timestamp_s > second.trigger_generation_s


def test_trigger_timestamp_is_stable_under_variable_cycle_timing() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    intervals = [(0.0, 0.11), (0.11, 0.33), (0.33, 0.37), (0.37, 0.59)]
    logs = [runner.run_cycle(i + 1, end, 720, 1056, [_reject_detection()], start)[0] for i, (start, end) in enumerate(intervals)]

    projected_offsets = [log.trigger_timestamp_s - log.trigger_generation_s for log in logs]
    assert all(offset > 1.0 for offset in projected_offsets)
    assert max(projected_offsets) - min(projected_offsets) < 0.05


def test_safe_fault_conditions_and_recovery_paths() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(
            MockTransportConfig(max_queue_depth=8, base_round_trip_ms=5.0, per_item_penalty_ms=1.0),
            fault_state=FaultState.SAFE,
        ),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )
    safe_logs = runner.run_cycle(1, 0.2, 720, 1056, [_reject_detection()], 0.1)
    assert safe_logs[0].ack_code.value == "NACK_SAFE"

    runner._transport.fault_state = FaultState.WATCHDOG  # type: ignore[attr-defined]
    watchdog_logs = runner.run_cycle(2, 0.3, 720, 1056, [_reject_detection()], 0.2)
    assert watchdog_logs[0].ack_code.value == "NACK_WATCHDOG"

    runner._transport.fault_state = FaultState.NORMAL  # type: ignore[attr-defined]
    recovered_logs = runner.run_cycle(3, 0.4, 720, 1056, [_reject_detection()], 0.3)
    assert recovered_logs[0].ack_code.value in {"ACK", "NACK_SAFE"}


def test_queue_timing_behavior_under_sustained_load() -> None:
    transport = MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=1.0, per_item_penalty_ms=0.5))
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=transport,
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    round_trips = []
    for idx in range(5):
        log = runner.run_cycle(idx + 1, 0.2 + idx * 0.1, 720, 1056, [_reject_detection()], 0.1 + idx * 0.1)[0]
        round_trips.append(log.protocol_round_trip_ms)

    assert round_trips == sorted(round_trips)


def test_stage_latency_fields_are_populated_for_each_log() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    logs = runner.run_cycle(
        frame_id=9,
        timestamp_s=0.9,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=0.8,
    )

    log = logs[0]
    assert log.ingest_latency_ms >= 0.0
    assert log.decision_latency_ms >= 0.0
    assert log.schedule_latency_ms >= 0.0
    assert log.transport_latency_ms >= 0.0
    assert log.cycle_latency_ms >= 0.0
    assert log.cycle_latency_ms >= log.transport_latency_ms


def test_encoder_dropout_ratio_quantization_behavior_is_deterministic() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(
            pulses_per_revolution=100,
            belt_speed_mm_per_s=100.0,
            pulley_circumference_mm=200.0,
            dropout_ratio=0.25,
        )
    )

    pulses = [encoder.pulses_between(i * 0.1, (i + 1) * 0.1) for i in range(20)]
    assert sum(pulses) == 71
    assert pulses.count(3) > 0
    assert pulses.count(4) > 0


def test_encoder_dropout_ratio_one_drops_all_pulses() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(
            pulses_per_revolution=100,
            belt_speed_mm_per_s=100.0,
            pulley_circumference_mm=200.0,
            dropout_ratio=1.0,
        )
    )

    pulses = [encoder.pulses_between(i * 0.1, (i + 1) * 0.1) for i in range(10)]
    assert sum(pulses) == 0


def test_projected_trigger_timestamp_is_deterministic_at_low_speed() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=20.0, pulley_circumference_mm=200.0)
    )

    projected = encoder.project_trigger_timestamp(
        trigger_generation_s=1.0,
        trigger_distance_mm=300.0,
        schedule_time_s=0.01,
    )

    assert projected == 16.01


def test_projected_trigger_timestamp_stops_advancing_under_zero_speed_fault() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0),
        fault_config=EncoderFaultConfig(force_zero_speed=True),
    )

    projected = encoder.project_trigger_timestamp(
        trigger_generation_s=2.0,
        trigger_distance_mm=150.0,
        schedule_time_s=0.02,
    )

    assert projected == 2.0


def test_trigger_generation_timestamp_uses_previous_pulse_when_dropout_hides_current_interval() -> None:
    encoder = VirtualEncoder(
        EncoderConfig(
            pulses_per_revolution=100,
            belt_speed_mm_per_s=100.0,
            pulley_circumference_mm=200.0,
            dropout_ratio=0.95,
        )
    )

    encoder.pulses_between(0.0, 0.5)
    first_generation = encoder.resolve_trigger_generation_timestamp(0.0)

    encoder.pulses_between(0.5, 0.6)
    second_generation = encoder.resolve_trigger_generation_timestamp(0.5)

    assert first_generation == 0.5
    assert second_generation == first_generation


def test_watchdog_summary_counts_ack_code_not_nack_code_aliases() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(
            MockTransportConfig(max_queue_depth=8, base_round_trip_ms=5.0, per_item_penalty_ms=1.0),
            fault_state=FaultState.WATCHDOG,
        ),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    watchdog_logs = runner.run_cycle(1, 0.2, 720, 1056, [_reject_detection()], 0.1)
    assert watchdog_logs[0].nack_code is None

    summary = BenchRunner.summarize(watchdog_logs)
    assert summary.watchdog_transitions == 1


def test_duplicate_frame_object_command_is_not_resent() -> None:
    transport = MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5))
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=transport,
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
    )

    detection = _reject_detection()
    first = runner.run_cycle(1, 0.2, 720, 1056, [detection], 0.1)[0]
    second = runner.run_cycle(1, 0.25, 720, 1056, [detection], 0.2)[0]

    assert first.actuator_command_issued is True
    assert first.command_source == "auto_pipeline"
    assert second.actuator_command_issued is False
    assert second.command_source == ""


def test_over_budget_cycle_forces_safe_and_skips_actuation() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
        safety=BenchSafetyConfig(detect_budget_ms=0.01),
    )

    log = runner.run_cycle(1, 0.2, 720, 1056, [_reject_detection()], 0.1, detect_latency_ms=1.0)[0]
    assert log.over_budget is True
    assert log.actuator_command_issued is False
    assert log.ack_code.value == "NACK_SAFE"


def test_queue_age_and_staleness_guards_force_safe_scheduling() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
        safety=BenchSafetyConfig(max_queue_age_ms=1.0, max_frame_staleness_ms=1.0),
    )

    now = time.perf_counter()
    log = runner.run_cycle(
        1,
        0.2,
        720,
        1056,
        [_reject_detection()],
        0.1,
        enqueued_monotonic_s=now - 1.0,
        captured_monotonic_s=now - 1.0,
    )[0]
    assert log.fault_event in {"QUEUE_AGE_EXCEEDED", "FRAME_STALENESS_EXCEEDED"}
    assert log.actuator_command_issued is False


def test_log_contains_provider_version_and_config_hash() -> None:
    runner = BenchRunner(
        pipeline=_build_pipeline(),
        transport=MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.5)),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)),
        provider_version="opencv_basic@2",
        model_version="n/a",
        active_config_hash="abc123",
    )
    log = runner.run_cycle(1, 0.2, 720, 1056, [_reject_detection()], 0.1, preprocess_metrics={"preprocess_valid": True})[0]
    assert log.detection_provider_version == "opencv_basic@2"
    assert log.active_config_hash == "abc123"
    assert log.preprocess_valid is True
