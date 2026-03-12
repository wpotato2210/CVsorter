from __future__ import annotations

from coloursorter.eval.reject_profiles import REJECTION_KEYS
from coloursorter.eval.rules import decision_outcome_for_object
from coloursorter.model import ObjectDetection


def test_capture_fault_precedence_overrides_threshold_reject() -> None:
    thresholds = {REJECTION_KEYS[2]: 1.0}
    detection = ObjectDetection(
        object_id="faulty-1",
        centroid_x_px=20.0,
        centroid_y_px=40.0,
        classification="reject",
        infection_score=1.0,
    )

    outcome = decision_outcome_for_object(
        detection,
        thresholds=thresholds,
        context_fault_reason="capture_fault_exposure",
    )

    assert outcome.decision == "unknown"
    assert outcome.reason_code == "capture_fault_exposure"


def test_fault_precedence_result_is_stable_across_repeated_runs() -> None:
    detection = ObjectDetection(
        object_id="faulty-2",
        centroid_x_px=10.0,
        centroid_y_px=11.0,
        classification="accept",
        infection_score=0.0,
    )

    outputs = [
        decision_outcome_for_object(detection, context_fault_reason="capture_fault_blur")
        for _ in range(5)
    ]

    assert {f"{outcome.decision}|{outcome.reason_code}" for outcome in outputs} == {"unknown|capture_fault_blur"}
