#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidencePaths:
    """Deterministic evidence input set for Phase 3 closeout."""

    protocol_vectors: Path
    timing_report_snapshot: Path
    trigger_correlation_vectors: Path
    hil_repeatability_vectors: Path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON in {path}")
    return payload


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_protocol_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    vectors = payload.get("vectors")
    if payload.get("vector_pack") is None or not isinstance(vectors, list) or not vectors:
        return False, "protocol vectors missing required vector_pack or non-empty vectors"
    return True, "ok"


def _validate_timing_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    report = payload.get("report")
    if not isinstance(report, list) or not report:
        return False, "timing snapshot must contain non-empty report list"
    required = {"id", "scenario_pass", "hard_gate_pass"}
    for row in report:
        if not isinstance(row, dict) or not required.issubset(row.keys()):
            return False, "timing report rows must include id/scenario_pass/hard_gate_pass"
    return True, "ok"


def _validate_trigger_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    vectors = payload.get("vectors")
    if payload.get("vector_pack") != "T3-003":
        return False, "trigger vector_pack must be T3-003"
    if not isinstance(vectors, list) or not vectors:
        return False, "trigger vectors must be non-empty"
    return True, "ok"


def _validate_hil_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    runs = payload.get("runs")
    if payload.get("vector_pack") != "T3-004":
        return False, "hil vector_pack must be T3-004"
    if payload.get("seed") != 3004:
        return False, "hil seed must be 3004"
    if not isinstance(runs, list) or not runs:
        return False, "hil runs must be non-empty"

    grouped_hashes: dict[str, set[str]] = {}
    for run in runs:
        if not isinstance(run, dict):
            return False, "hil run entries must be objects"
        scenario_id = str(run.get("scenario_id"))
        trace_hash = str(run.get("trace_hash"))
        grouped_hashes.setdefault(scenario_id, set()).add(trace_hash)
    inconsistent = sorted(scenario for scenario, hashes in grouped_hashes.items() if len(hashes) != 1)
    if inconsistent:
        return False, "hil rerun consistency failed for scenarios: " + ", ".join(inconsistent)
    return True, "ok"


def _build_bundle(inputs: EvidencePaths) -> dict[str, Any]:
    protocol_payload = _load_json(inputs.protocol_vectors)
    timing_payload = _load_json(inputs.timing_report_snapshot)
    trigger_payload = _load_json(inputs.trigger_correlation_vectors)
    hil_payload = _load_json(inputs.hil_repeatability_vectors)

    protocol_ok, protocol_detail = _validate_protocol_payload(protocol_payload)
    timing_ok, timing_detail = _validate_timing_payload(timing_payload)
    trigger_ok, trigger_detail = _validate_trigger_payload(trigger_payload)
    hil_ok, hil_detail = _validate_hil_payload(hil_payload)

    checks = {
        "protocol_parity": {"ok": protocol_ok, "detail": protocol_detail},
        "timing_envelope": {"ok": timing_ok, "detail": timing_detail},
        "trigger_correlation": {"ok": trigger_ok, "detail": trigger_detail},
        "hil_repeatability": {"ok": hil_ok, "detail": hil_detail},
    }

    overall_ok = all(check["ok"] for check in checks.values())
    return {
        "phase": "phase3",
        "task_id": "T3-006",
        "deterministic_inputs": {
            "protocol_vectors": str(inputs.protocol_vectors),
            "timing_report_snapshot": str(inputs.timing_report_snapshot),
            "trigger_correlation_vectors": str(inputs.trigger_correlation_vectors),
            "hil_repeatability_vectors": str(inputs.hil_repeatability_vectors),
        },
        "checks": checks,
        "fingerprints": {
            "protocol_parity": _fingerprint(protocol_payload),
            "timing_envelope": _fingerprint(timing_payload),
            "trigger_correlation": _fingerprint(trigger_payload),
            "hil_repeatability": _fingerprint(hil_payload),
        },
        "overall_ok": overall_ok,
    }


def _write_bundle(output_dir: Path, bundle: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / "phase3_evidence_bundle.json"
    report_path = output_dir / "phase3_closure_report.md"

    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    check_lines = []
    for check_name in sorted(bundle["checks"]):
        check = bundle["checks"][check_name]
        status = "PASS" if check["ok"] else "FAIL"
        check_lines.append(f"- {check_name}: {status} ({check['detail']})")

    report = "\n".join(
        [
            "# Phase 3 Evidence Bundle",
            "",
            "Task: T3-006",
            "",
            f"Overall: {'PASS' if bundle['overall_ok'] else 'FAIL'}",
            "",
            "## Deterministic checks",
            *check_lines,
            "",
            "## Fingerprints",
            *[f"- {name}: {value}" for name, value in sorted(bundle["fingerprints"].items())],
        ]
    )
    report_path.write_text(report + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Phase 3 sign-off evidence bundle")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/artifacts/phase3"),
        help="Bundle output directory.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate and print bundle without writing files.",
    )
    args = parser.parse_args()

    inputs = EvidencePaths(
        protocol_vectors=Path("tests/fixtures/protocol_vectors_t3_001.json"),
        timing_report_snapshot=Path("tests/fixtures/timing_jitter_t3_002_report_snapshot.json"),
        trigger_correlation_vectors=Path("tests/fixtures/trigger_correlation_t3_003.json"),
        hil_repeatability_vectors=Path("tests/fixtures/hil_gate_t3_004.json"),
    )

    bundle = _build_bundle(inputs)

    if args.verify_only:
        print(json.dumps(bundle, indent=2, sort_keys=True))
        return 0 if bool(bundle["overall_ok"]) else 1

    _write_bundle(args.output_dir, bundle)
    print(f"phase3_evidence_bundle={args.output_dir / 'phase3_evidence_bundle.json'}")
    print(f"phase3_closure_report={args.output_dir / 'phase3_closure_report.md'}")
    return 0 if bool(bundle["overall_ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
