from __future__ import annotations

import math

import pytest

from coloursorter.scheduler import build_scheduled_command


def test_compute_trigger_mm() -> None:
    command = build_scheduled_command(1, 42.125)
    assert command.lane == 1
    assert command.position_mm == 42.125


def test_reject_non_finite_trigger_mm() -> None:
    with pytest.raises(ValueError):
        build_scheduled_command(0, math.inf)
