from __future__ import annotations

from coloursorter.eval import rejection_reason_for_object
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
    assert rejection_reason_for_object(_base(infection_score=0.5)) == "infection_score_threshold"


def test_rejects_by_curve_score_threshold() -> None:
    assert rejection_reason_for_object(_base(curve_score=0.7)) == "curve_score_threshold"


def test_rejects_by_size_mm_threshold() -> None:
    assert rejection_reason_for_object(_base(size_mm=3.0)) == "size_mm_threshold"


def test_classification_reject_remains_supported() -> None:
    assert rejection_reason_for_object(_base(classification="reject")) == "classified_reject"


def test_accept_when_no_rule_matches() -> None:
    assert rejection_reason_for_object(_base()) is None


def test_rule_precedence_is_deterministic() -> None:
    reason = rejection_reason_for_object(
        _base(classification="reject", infection_score=0.6, curve_score=0.9, size_mm=6.0)
    )
    assert reason == "infection_score_threshold"
