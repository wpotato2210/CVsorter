from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import coloursorter.bench.cli as cli
from coloursorter.bench import BenchMode


def test_load_runtime_config_missing_file_returns_none(tmp_path: Path) -> None:
    """Boundary: runtime config loader returns None for absent path."""
    assert cli._load_runtime_config(tmp_path / "missing.yaml") is None


def test_select_scenarios_rejects_unknown_name() -> None:
    """Error: unknown scenario name raises deterministic ValueError."""
    with pytest.raises(ValueError, match="Unknown scenarios"):
        cli._select_scenarios(["not-a-scenario"], runtime_config=None)


def test_snapshot_frame_respects_enable_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Normal and boundary: disabled snapshot is empty; enabled snapshot writes via cv2."""
    monkeypatch.setattr(cli.cv2, "imwrite", lambda path, _frame: path.endswith(".png"), raising=False)
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cli._snapshot_frame(frame, tmp_path, frame_id=1, enabled=False) == ""
    path = cli._snapshot_frame(frame, tmp_path, frame_id=2, enabled=True)
    assert path.endswith("frame_000002.png")


def test_run_cycles_replay_collects_logs_and_releases_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Normal path: replay mode runs a cycle and always releases frame source."""

    class _FrameSource:
        released = False

        def __init__(self, *_args, **_kwargs):
            self._frame = SimpleNamespace(frame_id=3, timestamp_s=1.0, image_bgr=np.zeros((4, 5, 3), dtype=np.uint8))

        def open(self):
            return None

        def next_frame(self):
            frame, self._frame = self._frame, None
            return frame

        def release(self):
            self.released = True

    class _Detector:
        provider_version = "pv"
        model_version = "mv"
        active_config_hash = "hash"
        last_validation_metrics = {"preprocess_valid": True}

        def detect(self, _frame):
            return []

    runner = SimpleNamespace(process_ingest_payload=lambda _payload: ("log",))
    args = SimpleNamespace(
        mode=BenchMode.REPLAY.value,
        source="data",
        frame_period_s=0.1,
        camera_index=0,
        max_cycles=1,
        detector_provider="",
        detector_threshold=-1.0,
        camera_recipe="",
        lighting_recipe="",
        enable_snapshots=False,
        run_id="r",
        test_batch_id="b",
    )
    source = _FrameSource()
    monkeypatch.setattr(cli, "ReplayFrameSource", lambda *_a, **_k: source)
    monkeypatch.setattr(cli, "_build_detector", lambda *_a, **_k: _Detector())
    monkeypatch.setattr(cli.cv2, "cvtColor", lambda img, _code: img)
    logs = cli._run_cycles(args, runner, None, tmp_path, {})
    assert logs == ("log",)
    assert source.released is True


def test_module_main_passes_replay_args_to_bench(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint: replay options are forwarded as explicit argv to bench main."""
    import coloursorter.__main__ as module_main

    captured: list[str] = []

    def _fake_bench_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        captured.extend(argv)
        return 0

    monkeypatch.setattr(module_main, "bench_main", _fake_bench_main)
    rc = module_main.main(["--mode", "replay", "--source", "dataset", "--max-cycles", "9", "--artifact-root", "out"])
    assert rc == 0
    assert captured == [
        "--mode",
        "replay",
        "--source",
        "dataset",
        "--max-cycles",
        "9",
        "--artifact-root",
        "out",
    ]


def test_module_main_passes_live_args_without_mutating_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint: live mode forwards argv and leaves global sys.argv untouched."""
    import sys
    import coloursorter.__main__ as module_main

    original = ["prog", "--unchanged"]
    monkeypatch.setattr(sys, "argv", original.copy())

    captured: list[str] = []

    def _fake_bench_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        captured.extend(argv)
        return 0

    monkeypatch.setattr(module_main, "bench_main", _fake_bench_main)
    rc = module_main.main(["--mode", "live", "--source", "0"])
    assert rc == 0
    assert captured == [
        "--mode",
        "live",
        "--source",
        "0",
        "--max-cycles",
        "300",
        "--artifact-root",
        "artifacts/bench",
    ]
    assert sys.argv == original
