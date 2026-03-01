from __future__ import annotations

from pathlib import Path

from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig
from coloursorter.bench.runner import BenchRunner
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.bench.virtual_encoder import EncoderConfig, EncoderFaultConfig, VirtualEncoder
from coloursorter.config import RuntimeConfig
from coloursorter.deploy import PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection
from coloursorter.serial_interface import encode_schedule_command

FIXTURES = Path(__file__).parent / "fixtures"


def _build_pipeline() -> PipelineRunner:
    return PipelineRunner(
        lane_config_path=FIXTURES / "lane_geometry_22.yaml",
        calibration_path=FIXTURES / "calibration_edge_valid.json",
    )


def _reject_detection() -> ObjectDetection:
    return ObjectDetection(
        object_id="dry-run-1",
        centroid_x_px=120.0,
        centroid_y_px=240.0,
        classification="reject",
    )


def test_end_to_end_dry_run_detection_to_sched_serialization() -> None:
    pipeline = _build_pipeline()
    frame = FrameMetadata(frame_id=11, timestamp_s=0.5, image_height_px=720, image_width_px=1056)

    result = pipeline.run(frame=frame, detections=[_reject_detection()])

    assert len(result.decisions) == 1
    assert result.decisions[0].rejection_reason == "classified_reject"
    assert len(result.schedule_commands) == 1
    assert result.schedule_commands[0].to_wire() == "SCHED:2:304.630"
    assert encode_schedule_command(result.schedule_commands[0]) == b"<SCHED|2|304.630>\n"


def test_latency_budget_at_pipeline_transport_boundary_with_mock_clock() -> None:
    pipeline = _build_pipeline()
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=8, base_round_trip_ms=4.0, per_item_penalty_ms=1.0)
    )
    encoder = VirtualEncoder(
        config=EncoderConfig(
            pulses_per_revolution=100,
            belt_speed_mm_per_s=300.0,
            pulley_circumference_mm=200.0,
        )
    )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=encoder)

    # Mocked clock inputs at module boundary.
    logs = runner.run_cycle(
        frame_id=5,
        timestamp_s=1.050,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=1.000,
    )

    assert len(logs) == 1
    log = logs[0]
    assert log.trigger_generation_s == 1.050
    assert log.protocol_round_trip_ms <= 10.0
    assert log.ack_code == AckCode.ACK


def test_safe_transition_for_missing_pulses() -> None:
    pipeline = _build_pipeline()
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=8, base_round_trip_ms=5.0, per_item_penalty_ms=1.0),
        fault_state=FaultState.SAFE,
    )
    encoder = VirtualEncoder(
        config=EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0),
        fault_config=EncoderFaultConfig(force_missing_pulses=True),
    )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=encoder)

    logs = runner.run_cycle(
        frame_id=1,
        timestamp_s=2.0,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=1.9,
    )

    assert len(logs) == 1
    assert logs[0].trigger_generation_s == 1.9
    assert logs[0].ack_code == AckCode.NACK_SAFE


def test_safe_transition_for_zero_belt_speed() -> None:
    pipeline = _build_pipeline()
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=8, base_round_trip_ms=5.0, per_item_penalty_ms=1.0),
        fault_state=FaultState.SAFE,
    )
    encoder = VirtualEncoder(
        config=EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0),
        fault_config=EncoderFaultConfig(force_zero_speed=True),
    )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=encoder)

    logs = runner.run_cycle(
        frame_id=2,
        timestamp_s=3.0,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=2.9,
    )

    assert len(logs) == 1
    assert logs[0].trigger_generation_s == 2.9
    assert logs[0].ack_code == AckCode.NACK_SAFE


def test_safe_transition_for_missing_home_sensor_condition() -> None:
    # AUTO_HOME runtime mode + SAFE transport models home sensor unavailable at startup.
    config = RuntimeConfig.from_text("motion_mode: FOLLOW_BELT\nhoming_mode: AUTO_HOME\n")
    assert config.homing_mode == "AUTO_HOME"

    pipeline = _build_pipeline()
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=8, base_round_trip_ms=5.0, per_item_penalty_ms=1.0),
        fault_state=FaultState.SAFE,
    )
    encoder = VirtualEncoder(
        config=EncoderConfig(pulses_per_revolution=100, belt_speed_mm_per_s=300.0, pulley_circumference_mm=200.0)
    )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=encoder)

    logs = runner.run_cycle(
        frame_id=3,
        timestamp_s=4.0,
        image_height_px=720,
        image_width_px=1056,
        detections=[_reject_detection()],
        previous_timestamp_s=3.95,
    )

    assert len(logs) == 1
    assert logs[0].ack_code == AckCode.NACK_SAFE
