from __future__ import annotations

MODE_TRANSITIONS: dict[str, frozenset[str]] = {
    "AUTO": frozenset({"AUTO", "MANUAL", "SAFE"}),
    "MANUAL": frozenset({"AUTO", "MANUAL", "SAFE"}),
    "SAFE": frozenset({"SAFE", "MANUAL"}),
}


def is_mode_transition_allowed(current_mode: str, target_mode: str) -> bool:
    return target_mode in MODE_TRANSITIONS.get(current_mode, frozenset())
