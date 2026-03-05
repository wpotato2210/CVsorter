from __future__ import annotations

from coloursorter.bench.acceptance_pack import (
    AcceptanceExample,
    AcceptanceThresholds,
    Phase1BaselineInputs,
    acceptance_gate_passed,
    evaluate_acceptance_pack,
    evaluate_phase1_baseline,
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


def test_phase1_baseline_passes_with_target_values() -> None:
    result = evaluate_phase1_baseline(
        Phase1BaselineInputs(
            replay_setup_seconds=175.0,
            calibration_successes=49,
            calibration_sessions=50,
            artifact_parameter_overrides_logged=4,
            artifact_parameter_overrides_expected=4,
            scenario_thresholds_reported=5,
            scenario_thresholds_expected=5,
            transport_protocol_shape_mismatches=0,
        )
    )

    assert result.replay_timing_passed is True
    assert result.calibration_reliability_passed is True
    assert result.artifact_completeness_passed is True
    assert result.scenario_threshold_coverage_passed is True
    assert result.transport_parity_passed is True
    assert result.passed is True


def test_phase1_baseline_fails_when_any_target_misses() -> None:
    result = evaluate_phase1_baseline(
        Phase1BaselineInputs(
            replay_setup_seconds=181.0,
            calibration_successes=48,
            calibration_sessions=50,
            artifact_parameter_overrides_logged=3,
            artifact_parameter_overrides_expected=4,
            scenario_thresholds_reported=4,
            scenario_thresholds_expected=5,
            transport_protocol_shape_mismatches=2,
        )
    )

    assert result.replay_timing_passed is False
    assert result.calibration_reliability_passed is False
    assert result.artifact_completeness_passed is False
    assert result.scenario_threshold_coverage_passed is False
    assert result.transport_parity_passed is False
    assert result.passed is False


def test_phase1_baseline_calibration_handles_non_positive_denominator() -> None:
    result = evaluate_phase1_baseline(
        Phase1BaselineInputs(
            replay_setup_seconds=100.0,
            calibration_successes=0,
            calibration_sessions=0,
            artifact_parameter_overrides_logged=0,
            artifact_parameter_overrides_expected=0,
            scenario_thresholds_reported=0,
            scenario_thresholds_expected=0,
            transport_protocol_shape_mismatches=0,
        )
    )

    assert result.calibration_reliability_passed is False
