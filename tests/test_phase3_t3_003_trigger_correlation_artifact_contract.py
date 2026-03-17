from __future__ import annotations

from pathlib import Path


ARTIFACT_PATH = Path("docs/artifacts/t3_003_trigger_correlation_design.md")


def test_t3_003_artifact_declares_release_gating_scope() -> None:
    content = ARTIFACT_PATH.read_text(encoding="utf-8")

    assert "strict deterministic release-gating" in content
    assert "accepted `SCHED` command -> exactly one terminal status" in content


def test_t3_003_artifact_no_placeholder_or_non_gating_language() -> None:
    content = ARTIFACT_PATH.read_text(encoding="utf-8").lower()

    assert "placeholder" not in content
    assert "non-release gating" not in content
    assert "xfail" not in content
