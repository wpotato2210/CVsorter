from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from coloursorter.calibration import CalibrationError, load_calibration
from coloursorter.eval import rejection_reason_for_object
from coloursorter.model import CentroidMM, DecisionPayload, FrameMetadata, ObjectDetection
from coloursorter.preprocess import lane_for_x_px, lane_geometry_for_frame, load_lane_geometry
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
        self._lane_config_path = Path(lane_config_path)
        self._calibration_path = Path(calibration_path)
        self._geometry = load_lane_geometry(self._lane_config_path)
        self._calibration = None
        self._calibration_error: str | None = None
        self._lane_mtime_ns = self._lane_config_path.stat().st_mtime_ns
        self._calibration_mtime_ns = -1
        self._reload_calibration_if_changed(force=True)

    def _reload_lane_geometry_if_changed(self) -> None:
        current_mtime_ns = self._lane_config_path.stat().st_mtime_ns
        if current_mtime_ns == self._lane_mtime_ns:
            return
        self._geometry = load_lane_geometry(self._lane_config_path)
        self._lane_mtime_ns = current_mtime_ns

    def _reload_calibration_if_changed(self, force: bool = False) -> None:
        current_mtime_ns = self._calibration_path.stat().st_mtime_ns
        if not force and current_mtime_ns == self._calibration_mtime_ns:
            return
        try:
            self._calibration = load_calibration(self._calibration_path)
            self._calibration_error = None
        except CalibrationError as exc:
            self._calibration = None
            self._calibration_error = str(exc)
        self._calibration_mtime_ns = current_mtime_ns

    def run(
        self,
        frame: FrameMetadata,
        detections: list[ObjectDetection],
        thresholds: Mapping[str, float] | None = None,
    ) -> PipelineResult:
        decisions: list[DecisionPayload] = []
        commands: list[ScheduledCommand] = []
        self._reload_lane_geometry_if_changed()
        self._reload_calibration_if_changed()
        calibration = self._calibration
        calibration_error = self._calibration_error

        frame_lane_geometry = lane_geometry_for_frame(frame, self._geometry)
        lane_geometry = frame_lane_geometry.lane_geometry
        alignment_fault = frame_lane_geometry.alignment_reason

        scheduled_events: list[ScheduledDecision] = []

        for detection in detections:
            lane = lane_for_x_px(detection.centroid_x_px, lane_geometry)
            reason = calibration_error or alignment_fault

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
                reason = reason or rejection_reason_for_object(detection, thresholds=thresholds)

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

            if lane is not None and reason is not None and calibration_error is None and alignment_fault is None:
                command = build_scheduled_command(lane, trigger_mm)
                commands.append(command)
                scheduled_events.append(ScheduledDecision(object_id=detection.object_id, decision=decision, command=command))

        return PipelineResult(
            decisions=tuple(decisions),
            schedule_commands=tuple(commands),
            scheduled_events=tuple(scheduled_events),
        )
