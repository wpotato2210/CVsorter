from __future__ import annotations

from coloursorter.model import ObjectDetection


INFECTION_SCORE_THRESHOLD = 0.5
CURVE_SCORE_THRESHOLD = 0.7
SIZE_MM_THRESHOLD = 3.0


def rejection_reason_for_object(detection: ObjectDetection) -> str | None:
    if detection.infection_score >= INFECTION_SCORE_THRESHOLD:
        return "infection_score_threshold"
    if detection.curve_score >= CURVE_SCORE_THRESHOLD:
        return "curve_score_threshold"
    if detection.size_mm >= SIZE_MM_THRESHOLD:
        return "size_mm_threshold"
    if detection.classification.lower() == "reject":
        return "classified_reject"
    return None
