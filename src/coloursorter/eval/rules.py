from __future__ import annotations

from coloursorter.model import ObjectDetection


def rejection_reason_for_object(detection: ObjectDetection) -> str | None:
    if detection.classification.lower() == "reject":
        return "classified_reject"
    return None
