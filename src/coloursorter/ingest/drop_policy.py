from __future__ import annotations

from enum import Enum


class DeterministicDropPolicy(str, Enum):
    """Deterministic overflow strategy for bounded ingest queues."""

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
