from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.cli import _parse_args
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts
from coloursorter.bench.frame_source import FrameSourceError
from coloursorter.bench.replay_source import ReplayConfig, ReplayFrameSource


def _entry(**overrides: object) -> BenchLogEntry:
    payload: dict[str, object] = {
        "run_id": "r1",
        "test_batch_id": "b1",
        "event_timestamp_utc": "2024-01-01T00:00:00+00:00",
        "frame_timestamp_s": 0.0,
        "frame_id": 1,
        "object_id": "obj-1",
        "trigger_generation_s": 0.0,
        "lane": 0,
        "decision": "accept",
        "prediction_label": "accept",
        "confidence": 0.5,
        "rejection_reason": None,
        "protocol_round_trip_ms": 5.0,
        "ack_code": AckCode.ACK,
    }
    payload.update(overrides)
    return BenchLogEntry(**payload)


def test_replay_source_rejects_unsupported_input_deterministically(tmp_path: Path) -> None:
    source = ReplayFrameSource(tmp_path / "does_not_exist.bin", ReplayConfig(frame_period_s=0.1))

    with pytest.raises(FrameSourceError, match="Unsupported replay source"):
        source.open()


def test_replay_artifact_directory_and_filenames_are_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    logs = (_entry(),)
    scenarios = (BenchScenario("nominal", max_avg_rtt_ms=10.0, max_peak_rtt_ms=10.0, require_safe_transition=False, require_recovery=False),)
    evaluation = evaluate_logs(logs=logs, scenarios=scenarios)

    from datetime import datetime, timezone

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    monkeypatch.setattr("coloursorter.bench.evaluation.datetime", _FrozenDatetime)

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=False)

    assert artifact_dir.name == "20240102T030405Z"
    assert sorted(path.name for path in artifact_dir.iterdir()) == [
        "audit_trail.jsonl",
        "events.jsonl",
        "summary.json",
        "telemetry.csv",
    ]

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is True


def test_replay_cli_parser_enforces_required_option_values() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--mode", "replay", "--max-cycles", "abc"])
