from __future__ import annotations

from coloursorter.eval.rules import decision_outcome_for_object
from coloursorter.eval.reject_profiles import REJECTION_KEYS
from coloursorter.model import ObjectDetection


def _detection(score: float) -> ObjectDetection:
    return ObjectDetection(
        object_id="obj-1",
        centroid_x_px=100.0,
        centroid_y_px=50.0,
        classification="accept",
        infection_score=score,
    )


def test_identical_inputs_produce_identical_outputs() -> None:
    thresholds = {REJECTION_KEYS[2]: 50.0}
    detection = _detection(score=0.51)

    run_a = decision_outcome_for_object(detection, thresholds=thresholds)
    run_b = decision_outcome_for_object(detection, thresholds=thresholds)

    assert run_a == run_b
    assert run_a.decision == "reject"
    assert run_a.reason_code == "infection_score_threshold"


def test_threshold_boundary_behavior_is_deterministic() -> None:
    epsilon = 0.0001
    threshold = 0.5
    thresholds = {REJECTION_KEYS[2]: threshold * 100.0}

    below = decision_outcome_for_object(_detection(threshold - epsilon), thresholds=thresholds)
    at = decision_outcome_for_object(_detection(threshold), thresholds=thresholds)
    above = decision_outcome_for_object(_detection(threshold + epsilon), thresholds=thresholds)

    assert below.decision == "accept"
    assert below.reason_code == "accepted"
    assert at.decision == "reject"
    assert at.reason_code == "infection_score_threshold"
    assert above.decision == "reject"
    assert above.reason_code == "infection_score_threshold"


def test_repeated_runs_are_byte_stable_for_outcome_fields() -> None:
    thresholds = {REJECTION_KEYS[2]: 25.0}
    detection = _detection(0.25)

    fingerprints = {
        f"{decision_outcome_for_object(detection, thresholds=thresholds).decision}|"
        f"{decision_outcome_for_object(detection, thresholds=thresholds).reason_code}"
        for _ in range(8)
    }

    assert fingerprints == {"reject|infection_score_threshold"}
