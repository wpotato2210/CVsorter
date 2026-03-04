from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from coloursorter.eval.reject_profiles import REJECTION_KEYS, default_profile
from coloursorter.model import ObjectDetection

INFECTION_SCORE_PROFILE_KEY = REJECTION_KEYS[2]
CURVE_SCORE_PROFILE_KEY = REJECTION_KEYS[4]
SIZE_MM_PROFILE_KEY = REJECTION_KEYS[5]

DEFAULT_REJECTION_THRESHOLDS = default_profile().thresholds
_PROFILE_TO_RULE_VALUE_SCALE = 0.01

DECISION_ACCEPT = "accept"
DECISION_REJECT = "reject"
DECISION_UNKNOWN = "unknown"
DECISION_REASON_ACCEPTED = "accepted"


@dataclass(frozen=True)
class DecisionOutcome:
    decision: str
    reason_code: str


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


def decision_outcome_for_object(
    detection: ObjectDetection,
    thresholds: Mapping[str, float] | None = None,
    context_fault_reason: str | None = None,
) -> DecisionOutcome:
    if context_fault_reason is not None:
        return DecisionOutcome(decision=DECISION_UNKNOWN, reason_code=context_fault_reason)
    reason = rejection_reason_for_object(detection, thresholds=thresholds)
    if reason is not None:
        return DecisionOutcome(decision=DECISION_REJECT, reason_code=reason)
    return DecisionOutcome(decision=DECISION_ACCEPT, reason_code=DECISION_REASON_ACCEPTED)


def _score_threshold_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    return _profile_value_for_key(key, thresholds) * _PROFILE_TO_RULE_VALUE_SCALE


def _size_threshold_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    return _profile_value_for_key(key, thresholds) * _PROFILE_TO_RULE_VALUE_SCALE


def _profile_value_for_key(key: str, thresholds: Mapping[str, float] | None) -> float:
    if thresholds is not None and key in thresholds:
        return float(thresholds[key])
    return float(DEFAULT_REJECTION_THRESHOLDS[key])
