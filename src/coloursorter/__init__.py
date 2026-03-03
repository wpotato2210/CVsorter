"""Deterministic ColourSorter pipeline package."""

from __future__ import annotations

from typing import Any

__all__ = ["PipelineRunner", "PipelineResult"]


def __getattr__(name: str) -> Any:
    if name in {"PipelineRunner", "PipelineResult"}:
        from .deploy.pipeline import PipelineResult, PipelineRunner

        exported = {
            "PipelineRunner": PipelineRunner,
            "PipelineResult": PipelineResult,
        }
        return exported[name]
    raise AttributeError(f"module 'coloursorter' has no attribute {name!r}")
