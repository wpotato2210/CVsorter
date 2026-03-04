from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceExample:
    scenario: str
    predicted: str
    ground_truth: str


@dataclass(frozen=True)
class AcceptanceMetrics:
    precision: float
    recall: float
    false_accept_rate: float
    false_reject_rate: float


@dataclass(frozen=True)
class AcceptanceThresholds:
    min_precision: float = 0.85
    min_recall: float = 0.85
    max_far: float = 0.10
    max_frr: float = 0.10


def evaluate_acceptance_pack(samples: tuple[AcceptanceExample, ...]) -> AcceptanceMetrics:
    tp = fp = tn = fn = 0
    for sample in samples:
        predicted_reject = sample.predicted == "reject"
        truth_reject = sample.ground_truth == "reject"
        if predicted_reject and truth_reject:
            tp += 1
        elif predicted_reject and not truth_reject:
            fp += 1
        elif not predicted_reject and truth_reject:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    false_accept_rate = fp / (fp + tn) if (fp + tn) else 0.0
    false_reject_rate = fn / (fn + tp) if (fn + tp) else 0.0
    return AcceptanceMetrics(
        precision=precision,
        recall=recall,
        false_accept_rate=false_accept_rate,
        false_reject_rate=false_reject_rate,
    )


def acceptance_gate_passed(metrics: AcceptanceMetrics, thresholds: AcceptanceThresholds | None = None) -> bool:
    gate = thresholds or AcceptanceThresholds()
    return (
        metrics.precision >= gate.min_precision
        and metrics.recall >= gate.min_recall
        and metrics.false_accept_rate <= gate.max_far
        and metrics.false_reject_rate <= gate.max_frr
    )
