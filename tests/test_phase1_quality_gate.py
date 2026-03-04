from __future__ import annotations

from coloursorter.bench.acceptance_pack import (
    AcceptanceExample,
    AcceptanceThresholds,
    acceptance_gate_passed,
    evaluate_acceptance_pack,
)
from coloursorter.deploy.detection import CaptureBaselineConfig, capture_fault_reason
from coloursorter.eval.rules import (
    DECISION_ACCEPT,
    DECISION_REJECT,
    DECISION_UNKNOWN,
    decision_outcome_for_object,
)
from coloursorter.model import ObjectDetection


def _detection(**overrides: float | str) -> ObjectDetection:
    payload = {
        "object_id": "bean-1",
        "centroid_x_px": 10.0,
        "centroid_y_px": 12.0,
        "classification": "accept",
        "infection_score": 0.0,
        "curve_score": 0.0,
        "size_mm": 0.0,
    }
    payload.update(overrides)
    return ObjectDetection(**payload)


def test_decision_output_is_deterministic_with_reason_codes() -> None:
    rejected = decision_outcome_for_object(_detection(classification="reject"))
    accepted = decision_outcome_for_object(_detection())
    unknown = decision_outcome_for_object(_detection(), context_fault_reason="capture_luma_low")

    assert rejected.decision == DECISION_REJECT
    assert rejected.reason_code == "classified_reject"
    assert accepted.decision == DECISION_ACCEPT
    assert accepted.reason_code == "accepted"
    assert unknown.decision == DECISION_UNKNOWN
    assert unknown.reason_code == "capture_luma_low"


def test_capture_baseline_fault_reason_order_is_stable() -> None:
    config = CaptureBaselineConfig(min_luma=90.0, max_luma=160.0, max_exposure_gain=2.0, max_clipped_ratio=0.05)

    assert capture_fault_reason({"preprocess_valid": False}, config) == "capture_preprocess_invalid"
    assert capture_fault_reason({"preprocess_valid": True, "luma_after": 80.0}, config) == "capture_luma_low"
    assert capture_fault_reason({"preprocess_valid": True, "luma_after": 170.0}, config) == "capture_luma_high"
    assert (
        capture_fault_reason({"preprocess_valid": True, "luma_after": 120.0, "exposure_gain": 2.1}, config)
        == "capture_exposure_gain_high"
    )
    assert (
        capture_fault_reason(
            {"preprocess_valid": True, "luma_after": 120.0, "exposure_gain": 1.0, "clipped_ratio": 0.06},
            config,
        )
        == "capture_clipping_high"
    )


def test_acceptance_pack_metrics_pass_on_repeat_runs() -> None:
    samples = (
        AcceptanceExample(scenario="nominal", predicted="accept", ground_truth="accept"),
        AcceptanceExample(scenario="nominal", predicted="reject", ground_truth="reject"),
        AcceptanceExample(scenario="glare", predicted="reject", ground_truth="reject"),
        AcceptanceExample(scenario="overlap", predicted="reject", ground_truth="reject"),
        AcceptanceExample(scenario="overlap", predicted="accept", ground_truth="accept"),
        AcceptanceExample(scenario="low-contrast", predicted="accept", ground_truth="accept"),
        AcceptanceExample(scenario="low-contrast", predicted="reject", ground_truth="reject"),
        AcceptanceExample(scenario="low-contrast", predicted="accept", ground_truth="accept"),
    )
    thresholds = AcceptanceThresholds(min_precision=0.85, min_recall=0.85, max_far=0.2, max_frr=0.2)

    first = evaluate_acceptance_pack(samples)
    second = evaluate_acceptance_pack(samples)

    assert first == second
    assert first.precision == 1.0
    assert first.recall == 1.0
    assert first.false_accept_rate == 0.0
    assert first.false_reject_rate == 0.0
    assert acceptance_gate_passed(first, thresholds)
