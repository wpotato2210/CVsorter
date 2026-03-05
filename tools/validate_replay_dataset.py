#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_CANDIDATES = [
    "manifest.json",
    "dataset_manifest.json",
]


def _load_json(path: Path) -> tuple[bool, str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _validate_dataset(dataset_path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "dataset_path": str(dataset_path),
        "exists": dataset_path.exists(),
        "required_files": {},
        "schema_validity": {},
        "corrupted_frames": [],
        "complete": False,
    }
    if not dataset_path.exists():
        return report

    manifest_path = next((dataset_path / name for name in REQUIRED_CANDIDATES if (dataset_path / name).exists()), None)
    for name in REQUIRED_CANDIDATES:
        report["required_files"][name] = (dataset_path / name).exists()

    frame_files = list(dataset_path.rglob("*.json"))
    for frame_file in frame_files:
        valid, reason = _load_json(frame_file)
        report["schema_validity"][str(frame_file.relative_to(dataset_path))] = valid
        if not valid:
            report["corrupted_frames"].append({"file": str(frame_file.relative_to(dataset_path)), "error": reason})

    report["manifest_detected"] = str(manifest_path.relative_to(dataset_path)) if manifest_path else None
    report["complete"] = manifest_path is not None and len(report["corrupted_frames"]) == 0
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate replay dataset completeness and json integrity")
    parser.add_argument("--dataset", required=True, help="Path to replay dataset")
    parser.add_argument("--output", default="artifacts/replay_dataset_validation.json", help="Output JSON report")
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    output_path = Path(args.output)
    report = _validate_dataset(dataset_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"complete": report["complete"], "corrupted": len(report["corrupted_frames"])}, indent=2))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
