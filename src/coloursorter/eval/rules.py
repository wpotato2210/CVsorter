from __future__ import annotations

from collections.abc import Mapping

from coloursorter.eval.reject_profiles import REJECTION_KEYS, default_profile
from coloursorter.model import ObjectDetection

INFECTION_SCORE_PROFILE_KEY = REJECTION_KEYS[2]
CURVE_SCORE_PROFILE_KEY = REJECTION_KEYS[4]
SIZE_MM_PROFILE_KEY = REJECTION_KEYS[5]

DEFAULT_REJECTION_THRESHOLDS = default_profile().thresholds
_PROFILE_TO_RULE_VALUE_SCALE = 0.01


def rejection_reason_for_object(
    detection: ObjectDetection,
    thresholds: Mapping[str, float] | None = None,
) -> str | None:
    if detection.infection_score >= _score_threshold_for_key(INFECTION_SCORE_PROFILE_KEY, thresholds):
        return "infection_score_threshold"
    if detection.curve_score >= _score_threshold_for_key(CURVE_SCORE_PROFILE_KEY, thresholds):
        return "curve_score_threshold"
    if detection.size_mm >= _size_threshold_for_key(SIZE_MM_PROFILE_KEY, thresholds):
        return "size_mm_threshold"
    if detection.classification.lower() == "reject":
        return "classified_reject"
    return None


def _score_threshold_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    return _profile_value_for_key(key, thresholds) * _PROFILE_TO_RULE_VALUE_SCALE


def _size_threshold_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    return _profile_value_for_key(key, thresholds) * _PROFILE_TO_RULE_VALUE_SCALE


def _profile_value_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    if thresholds is not None and key in thresholds:
        return float(thresholds[key])
    return float(DEFAULT_REJECTION_THRESHOLDS[key])
