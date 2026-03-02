from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from coloursorter.calibration import CalibrationError, load_calibration
from coloursorter.eval import rejection_reason_for_object
from coloursorter.model import CentroidMM, DecisionPayload, FrameMetadata, ObjectDetection
from coloursorter.preprocess import lane_for_x_px, load_lane_geometry
from coloursorter.scheduler import ScheduledCommand, build_scheduled_command


@dataclass(frozen=True)
class PipelineResult:
    decisions: tuple[DecisionPayload, ...]
    schedule_commands: tuple[ScheduledCommand, ...]
    scheduled_events: tuple["ScheduledDecision", ...] = ()


@dataclass(frozen=True)
class ScheduledDecision:
    object_id: str
    decision: DecisionPayload
    command: ScheduledCommand


class PipelineRunner:
    def __init__(self, lane_config_path: str | Path, calibration_path: str | Path) -> None:
        self._geometry = load_lane_geometry(lane_config_path)
        self._calibration_path = calibration_path

    def run(
        self,
        frame: FrameMetadata,
        detections: list[ObjectDetection],
    ) -> PipelineResult:
        decisions: list[DecisionPayload] = []
        commands: list[ScheduledCommand] = []

        try:
            calibration = load_calibration(self._calibration_path)
            calibration_error: str | None = None
        except CalibrationError as exc:
            calibration = None
            calibration_error = str(exc)

        scheduled_events: list[ScheduledDecision] = []

        for detection in detections:
            lane = lane_for_x_px(detection.centroid_x_px, self._geometry)
            reason = calibration_error

            if lane is None:
                reason = reason or "out_of_lane_bounds"
                centroid_mm = CentroidMM(x_mm=0.0, y_mm=0.0)
                trigger_mm = 0.0
            elif calibration is None:
                centroid_mm = CentroidMM(x_mm=0.0, y_mm=0.0)
                trigger_mm = 0.0
            else:
                centroid_mm = CentroidMM(
                    x_mm=calibration.px_to_mm(detection.centroid_x_px),
                    y_mm=calibration.px_to_mm(detection.centroid_y_px),
                )
                trigger_mm = self._geometry.camera_to_reject_mm + centroid_mm.y_mm
                reason = reason or rejection_reason_for_object(detection)

            decision = DecisionPayload(
                frame_id=frame.frame_id,
                object_id=detection.object_id,
                lane=-1 if lane is None else lane,
                centroid_mm=centroid_mm,
                trigger_mm=trigger_mm,
                classification=detection.classification,
                rejection_reason=reason,
            )
            decisions.append(decision)

            if lane is not None and reason is not None and reason != calibration_error:
                command = build_scheduled_command(lane, trigger_mm)
                commands.append(command)
                scheduled_events.append(ScheduledDecision(object_id=detection.object_id, decision=decision, command=command))

        return PipelineResult(
            decisions=tuple(decisions),
            schedule_commands=tuple(commands),
            scheduled_events=tuple(scheduled_events),
        )
