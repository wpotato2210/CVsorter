from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class _SchedulerTrace:
    """Deterministic function-call trace for scheduler path-isolation checks."""

    calls: list[str] = field(default_factory=list)
    selected_mode: str = "legacy"

    def legacy_enqueue(self, lane: int, trigger_mm: float) -> tuple[int, float]:
        self.calls.append(f"legacy:{lane}:{trigger_mm:.3f}")
        return lane, trigger_mm

    def extended_enqueue(self, lane: int, trigger_mm: float) -> tuple[int, float]:
        self.calls.append(f"extended:{lane}:{trigger_mm:.3f}")
        return lane, trigger_mm


def _protocol_major_from_env() -> int:
    raw = os.environ.get("PROTOCOL_VERSION", "1").strip()
    try:
        return int(raw)
    except ValueError:
        return 1


def _dispatch_scheduler(trace: _SchedulerTrace, lane: int, trigger_mm: float, *, use_extended: bool = False) -> tuple[int, float]:
    protocol_major = _protocol_major_from_env()

    if protocol_major <= 1:
        trace.selected_mode = "legacy"
        return trace.legacy_enqueue(lane, trigger_mm)

    if use_extended:
        trace.selected_mode = "extended"
        return trace.extended_enqueue(lane, trigger_mm)

    trace.selected_mode = "legacy"
    return trace.legacy_enqueue(lane, trigger_mm)


def test_protocol_v1_calls_only_legacy_scheduler_entry_points(monkeypatch) -> None:
    trace = _SchedulerTrace()
    monkeypatch.setenv("PROTOCOL_VERSION", "1")

    outcome = _dispatch_scheduler(trace, 3, 250.0, use_extended=True)

    assert outcome == (3, 250.0)
    assert trace.selected_mode == "legacy"
    assert trace.calls == ["legacy:3:250.000"]
    assert all(not call.startswith("extended:") for call in trace.calls)


def test_protocol_v2plus_keeps_legacy_default_unless_explicitly_switched(monkeypatch) -> None:
    trace = _SchedulerTrace()
    monkeypatch.setenv("PROTOCOL_VERSION", "2")

    legacy_outcome = _dispatch_scheduler(trace, 1, 100.0)
    extended_outcome = _dispatch_scheduler(trace, 1, 100.0, use_extended=True)

    assert legacy_outcome == (1, 100.0)
    assert extended_outcome == (1, 100.0)
    assert trace.calls == ["legacy:1:100.000", "extended:1:100.000"]


def test_invalid_protocol_version_falls_back_to_v1_legacy_isolation(monkeypatch) -> None:
    trace = _SchedulerTrace()
    monkeypatch.setenv("PROTOCOL_VERSION", "invalid")

    _dispatch_scheduler(trace, 4, 444.0, use_extended=True)

    assert trace.selected_mode == "legacy"
    assert trace.calls == ["legacy:4:444.000"]
