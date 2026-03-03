from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.eval.reject_profiles import (
    RejectProfile,
    RejectProfileValidationError,
    load_reject_profiles,
    save_reject_profiles,
    selected_thresholds,
)


def _profile(name: str) -> RejectProfile:
    return RejectProfile(
        name=name,
        thresholds={
            "broken_snapped": 50.0,
            "immature_thin_small": 50.0,
            "rot": 50.0,
            "mould": 50.0,
            "curliness_degrees": 50.0,
            "length": 50.0,
            "visual_defects_spots_stripes": 50.0,
            "over_mature_beginning_seed_fill": 50.0,
        },
    )


def test_load_profiles_bootstraps_default_on_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "reject_profiles.yaml"
    profiles, selected = load_reject_profiles(path)
    assert selected == "standard_reject"
    assert len(profiles) == 1
    assert path.exists()


def test_save_profiles_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "reject_profiles.yaml"
    with pytest.raises(RejectProfileValidationError, match="Duplicate profile name"):
        save_reject_profiles(path, [_profile("dup"), _profile("dup")], selected_name="dup")


def test_selected_thresholds_returns_copy() -> None:
    profiles = [_profile("copy_test")]
    selected = selected_thresholds(profiles, "copy_test")
    selected["rot"] = 1.0
    assert profiles[0].thresholds["rot"] == 50.0
