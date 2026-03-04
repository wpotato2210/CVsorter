from __future__ import annotations

from coloursorter.eval import rejection_reason_for_object
from coloursorter.model import ObjectDetection


def test_rejection_reason_for_reject_classification_is_set() -> None:
    detection = ObjectDetection("obj-reject", 5.0, 5.0, "reject")

    assert rejection_reason_for_object(detection) == "classified_reject"


def test_rejection_reason_for_non_reject_classification_is_none() -> None:
    detection = ObjectDetection("obj-accept", 5.0, 5.0, "accept")

    assert rejection_reason_for_object(detection) is None
