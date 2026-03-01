from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from coloursorter.bench import (
    BenchLogEntry,
    BenchMode,
    BenchRunner,
    EncoderConfig,
    LiveConfig,
    LiveFrameSource,
    MockMcuTransport,
    MockTransportConfig,
    ReplayConfig,
    ReplayFrameSource,
    VirtualEncoder,
    default_scenarios,
)
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts
from coloursorter.deploy import PipelineRunner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ColourSorter bench scenarios.")
    parser.add_argument("--mode", choices=[BenchMode.REPLAY.value, BenchMode.LIVE.value], default=BenchMode.REPLAY.value)
    parser.add_argument("--source", default="data", help="Replay source path (directory/video/image).")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--frame-period-s", type=float, default=1.0 / 30.0)
    parser.add_argument("--max-cycles", type=int, default=300)
    parser.add_argument("--scenario", action="append", default=[], help="Scenario profile name; can be repeated.")
    parser.add_argument("--artifact-root", default="artifacts/bench")
    parser.add_argument("--text-report", action="store_true")
    parser.add_argument("--lane-config", default="configs/lane_geometry.yaml")
    parser.add_argument("--calibration", default="configs/calibration.json")
    return parser.parse_args()


def _select_scenarios(names: list[str]):
    available = {scenario.name: scenario for scenario in default_scenarios()}
    selected_names = names or ["nominal"]
    missing = [name for name in selected_names if name not in available]
    if missing:
        raise ValueError(f"Unknown scenarios: {', '.join(missing)}")
    return tuple(available[name] for name in selected_names)


def _run_cycles(args: argparse.Namespace, runner: BenchRunner) -> tuple[BenchLogEntry, ...]:
    mode = BenchMode(args.mode)
    frame_source = (
        ReplayFrameSource(args.source, ReplayConfig(frame_period_s=args.frame_period_s))
        if mode == BenchMode.REPLAY
        else LiveFrameSource(LiveConfig(camera_index=args.camera_index, frame_period_s=args.frame_period_s))
    )
    frame_source.open()
    logs: list[BenchLogEntry] = []
    previous_timestamp_s = 0.0
    try:
        for _ in range(args.max_cycles):
            frame = frame_source.next_frame()
            if frame is None:
                break
            frame_rgb = cv2.cvtColor(frame.image_bgr, cv2.COLOR_BGR2RGB)
            cycle_logs = runner.run_cycle(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                image_height_px=frame_rgb.shape[0],
                image_width_px=frame_rgb.shape[1],
                detections=[],
                previous_timestamp_s=previous_timestamp_s,
            )
            logs.extend(cycle_logs)
            previous_timestamp_s = frame.timestamp_s
    finally:
        frame_source.release()
    return tuple(logs)


def main() -> int:
    args = _parse_args()
    scenarios = _select_scenarios(args.scenario)
    pipeline = PipelineRunner(lane_config_path=Path(args.lane_config), calibration_path=Path(args.calibration))
    transport = MockMcuTransport(MockTransportConfig(max_queue_depth=8, base_round_trip_ms=2.0, per_item_penalty_ms=0.8))
    encoder = EncoderConfig(
        pulses_per_revolution=2048,
        belt_speed_mm_per_s=140.0,
        pulley_circumference_mm=210.0,
        dropout_ratio=0.0,
    )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=VirtualEncoder(encoder))

    logs = _run_cycles(args, runner)
    evaluation = evaluate_logs(logs=logs, scenarios=scenarios)
    artifact_dir = write_artifacts(
        logs=logs,
        evaluation=evaluation,
        output_root=args.artifact_root,
        include_text_report=args.text_report,
    )
    print(f"artifact_dir={artifact_dir}")
    print(f"overall={'PASS' if evaluation.passed else 'FAIL'}")
    for result in evaluation.scenarios:
        print(f"{result.name}: {'PASS' if result.passed else 'FAIL'} - {result.detail}")
    return 0 if evaluation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
