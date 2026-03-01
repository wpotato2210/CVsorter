from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.calibration import CalibrationError, load_calibration

FIXTURES = Path(__file__).parent / "fixtures"


def test_calibration_zero_scale_edge_case_is_loadable() -> None:
    calibration = load_calibration(FIXTURES / "calibration_edge_zero.json")
    assert calibration.mm_per_pixel == 0.0
    assert calibration.px_to_mm(999.0) == 0.0


def test_calibration_invalid_hash_edge_case_fails_validation() -> None:
    with pytest.raises(CalibrationError, match="Invalid calibration hash"):
        load_calibration(FIXTURES / "calibration_edge_invalid_hash.json")
