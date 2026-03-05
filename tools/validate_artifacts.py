#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = (
    "replay_campaign_summary.json",
    "scenario_threshold_report.json",
    "transport_parity_report.json",
    "calibration_reliability_report.json",
)


REQUIRED_AUDIT_EVENTS = {
    "operator_action",
    "recipe_selection",
    "threshold_binding",
    "calibration_binding",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_bench_runs(replay_log_root: Path) -> list[Path]:
    if not replay_log_root.exists():
        return []
    return sorted(path for path in replay_log_root.iterdir() if path.is_dir())


def _validate_scheduler_payload(event: dict[str, Any]) -> list[str]:
    required = (
        "decision_label",
        "lane_index",
        "trigger_mm",
        "trigger_timestamp_s",
        "protocol_frame",
    )
    return [key for key in required if key not in event]


def _validate_decision_payload(event: dict[str, Any]) -> list[str]:
    required = (
        "prediction_label",
        "confidence",
        "decision_label",
        "decision_reason",
    )
    return [key for key in required if key not in event]


def _validate_audit_trail(audit_path: Path) -> dict[str, Any]:
    if not audit_path.exists():
        return {"ok": False, "missing_events": sorted(REQUIRED_AUDIT_EVENTS), "reason": "missing_audit_trail"}
    found: set[str] = set()
    for raw in audit_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        event_name = event.get("event")
        if isinstance(event_name, str):
            found.add(event_name)
    missing = sorted(REQUIRED_AUDIT_EVENTS - found)
    return {"ok": len(missing) == 0, "missing_events": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated acceptance artifacts")
    parser.add_argument("--artifacts", default="artifacts", help="Artifact root")
    args = parser.parse_args()

    artifact_root = Path(args.artifacts)
    replay_logs = artifact_root / "replay_run_logs"

    presence = {name: (artifact_root / name).exists() for name in REQUIRED_ARTIFACTS}
    run_dirs = _collect_bench_runs(replay_logs)

    scheduler_issues: list[dict[str, Any]] = []
    decision_issues: list[dict[str, Any]] = []
    audit_checks: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        events_path = run_dir / "events.jsonl"
        if events_path.exists():
            for line_no, raw in enumerate(events_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                event = json.loads(raw)
                missing_scheduler = _validate_scheduler_payload(event)
                if missing_scheduler:
                    scheduler_issues.append({"run": run_dir.name, "line": line_no, "missing": missing_scheduler})
                missing_decision = _validate_decision_payload(event)
                if missing_decision:
                    decision_issues.append({"run": run_dir.name, "line": line_no, "missing": missing_decision})
        audit_checks.append({"run": run_dir.name, **_validate_audit_trail(run_dir / "audit_trail.jsonl")})

    audit_ok = all(check["ok"] for check in audit_checks) if audit_checks else False
    overall_ok = all(presence.values()) and not scheduler_issues and not decision_issues and audit_ok

    report = {
        "overall_ok": overall_ok,
        "required_artifacts": presence,
        "runs_checked": len(run_dirs),
        "scheduler_payload_schema_ok": not scheduler_issues,
        "decision_payload_schema_ok": not decision_issues,
        "parameter_change_audit_ok": audit_ok,
        "scheduler_payload_issues": scheduler_issues,
        "decision_payload_issues": decision_issues,
        "audit_results": audit_checks,
    }

    out = artifact_root / "artifact_validation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"artifact_validation_report={out}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
