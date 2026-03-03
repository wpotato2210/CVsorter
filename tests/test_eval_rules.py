from __future__ import annotations

from coloursorter.eval import default_profile, rejection_reason_for_object
from coloursorter.eval.rules import CURVE_SCORE_PROFILE_KEY, INFECTION_SCORE_PROFILE_KEY, SIZE_MM_PROFILE_KEY
from coloursorter.model import ObjectDetection


def _base(**overrides: float | str) -> ObjectDetection:
    payload = {
        "object_id": "d1",
        "centroid_x_px": 1.0,
        "centroid_y_px": 2.0,
        "classification": "accept",
        "infection_score": 0.0,
        "curve_score": 0.0,
        "size_mm": 0.0,
    }
    payload.update(overrides)
    return ObjectDetection(**payload)


def test_rejects_by_infection_score_threshold() -> None:
    profile = default_profile().thresholds
    threshold = profile[INFECTION_SCORE_PROFILE_KEY] / 100.0
    assert rejection_reason_for_object(_base(infection_score=threshold + 1e-6)) == "infection_score_threshold"


def test_rejects_by_curve_score_threshold() -> None:
    profile = default_profile().thresholds
    threshold = profile[CURVE_SCORE_PROFILE_KEY] / 100.0
    assert rejection_reason_for_object(_base(curve_score=threshold)) == "curve_score_threshold"


def test_rejects_by_size_mm_threshold() -> None:
    profile = default_profile().thresholds
    threshold = profile[SIZE_MM_PROFILE_KEY] / 100.0
    assert rejection_reason_for_object(_base(size_mm=threshold)) == "size_mm_threshold"


def test_classification_reject_remains_supported() -> None:
    assert rejection_reason_for_object(_base(classification="reject")) == "classified_reject"


def test_accept_when_no_rule_matches() -> None:
    assert rejection_reason_for_object(_base()) is None


def test_rule_precedence_is_deterministic() -> None:
    reason = rejection_reason_for_object(
        _base(classification="reject", infection_score=0.9, curve_score=0.9, size_mm=0.9)
    )
    assert reason == "infection_score_threshold"


def test_uses_provided_thresholds_when_present() -> None:
    reason = rejection_reason_for_object(
        _base(infection_score=0.8),
        thresholds={INFECTION_SCORE_PROFILE_KEY: 90.0},
    )
    assert reason is None


def test_falls_back_to_default_profile_when_threshold_key_is_missing() -> None:
    profile = default_profile().thresholds
    threshold = profile[INFECTION_SCORE_PROFILE_KEY] / 100.0
    reason = rejection_reason_for_object(_base(infection_score=threshold + 1e-6), thresholds={SIZE_MM_PROFILE_KEY: 99.0})
    assert reason == "infection_score_threshold"
