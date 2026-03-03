from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REJECTION_KEYS: tuple[str, ...] = (
    "broken_snapped",
    "immature_thin_small",
    "rot",
    "mould",
    "curliness_degrees",
    "length",
    "visual_defects_spots_stripes",
    "over_mature_beginning_seed_fill",
)


class RejectProfileValidationError(ValueError):
    """Raised when reject profile data is invalid."""


@dataclass(frozen=True)
class RejectProfile:
    name: str
    thresholds: dict[str, float]

    def validated(self) -> RejectProfile:
        if not self.name.strip():
            raise RejectProfileValidationError("Profile name must be non-empty")
        normalized: dict[str, float] = {}
        for key in REJECTION_KEYS:
            if key not in self.thresholds:
                raise RejectProfileValidationError(f"Missing threshold: {key}")
            value = float(self.thresholds[key])
            if not 0.0 <= value <= 100.0:
                raise RejectProfileValidationError(f"Threshold out of range [0,100]: {key}={value}")
            normalized[key] = value
        return RejectProfile(name=self.name.strip(), thresholds=normalized)


def default_profile() -> RejectProfile:
    return RejectProfile(
        name="standard_reject",
        thresholds={
            "broken_snapped": 60.0,
            "immature_thin_small": 55.0,
            "rot": 35.0,
            "mould": 30.0,
            "curliness_degrees": 45.0,
            "length": 50.0,
            "visual_defects_spots_stripes": 40.0,
            "over_mature_beginning_seed_fill": 65.0,
        },
    ).validated()


def load_reject_profiles(path: str | Path) -> tuple[list[RejectProfile], str]:
    file_path = Path(path)
    if not file_path.exists():
        profile = default_profile()
        save_reject_profiles(file_path, [profile], selected_name=profile.name)
        return [profile], profile.name

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RejectProfileValidationError("Profile file must be a mapping")
    raw_profiles = payload.get("profiles", [])
    if not isinstance(raw_profiles, list):
        raise RejectProfileValidationError("'profiles' must be a list")

    profiles = [_parse_profile(item).validated() for item in raw_profiles]
    if not profiles:
        profiles = [default_profile()]

    selected_name = str(payload.get("selected_profile", profiles[0].name))
    names = {profile.name for profile in profiles}
    if selected_name not in names:
        selected_name = profiles[0].name

    _validate_unique_profile_names(profiles)
    return profiles, selected_name


def save_reject_profiles(path: str | Path, profiles: list[RejectProfile], selected_name: str) -> None:
    validated = [profile.validated() for profile in profiles]
    if not validated:
        raise RejectProfileValidationError("At least one profile is required")
    _validate_unique_profile_names(validated)
    if selected_name not in {profile.name for profile in validated}:
        raise RejectProfileValidationError("Selected profile is not in profiles list")

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "selected_profile": selected_name,
        "profiles": [{"name": profile.name, "thresholds": profile.thresholds} for profile in validated],
    }
    file_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def selected_thresholds(profiles: list[RejectProfile], selected_name: str) -> dict[str, float]:
    for profile in profiles:
        if profile.name == selected_name:
            return dict(profile.thresholds)
    raise RejectProfileValidationError(f"Unknown selected profile: {selected_name}")


def _validate_unique_profile_names(profiles: list[RejectProfile]) -> None:
    seen: set[str] = set()
    for profile in profiles:
        if profile.name in seen:
            raise RejectProfileValidationError(f"Duplicate profile name: {profile.name}")
        seen.add(profile.name)


def _parse_profile(raw_profile: Any) -> RejectProfile:
    if not isinstance(raw_profile, dict):
        raise RejectProfileValidationError("Each profile entry must be a mapping")
    name = str(raw_profile.get("name", "")).strip()
    thresholds = raw_profile.get("thresholds")
    if not isinstance(thresholds, dict):
        raise RejectProfileValidationError(f"Profile '{name or '<unnamed>'}' thresholds must be a mapping")
    return RejectProfile(name=name, thresholds={str(k): float(v) for k, v in thresholds.items()})
