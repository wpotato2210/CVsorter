from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from coloursorter.bench.replay_source import ReplayConfig, ReplayFrameSource


def _write_ordered_frames(root: Path) -> None:
    frames = (
        "frame_002.png",
        "frame_000.png",
        "frame_001.png",
    )
    for file_name in frames:
        (root / file_name).write_bytes(b"replay-frame")


def _collect_replay_signature(source: ReplayFrameSource) -> list[tuple[int, float, int]]:
    source.open()
    signature: list[tuple[int, float, int]] = []
    while True:
        frame = source.next_frame()
        if frame is None:
            break
        signature.append((frame.frame_id, frame.timestamp_s, int(frame.image_bgr[0, 0, 0])))
    source.release()
    return signature


def test_replay_source_directory_is_deterministic_across_repeated_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_ordered_frames(tmp_path)

    def _fake_imread(path: str) -> np.ndarray:
        frame_value = int(Path(path).stem.rsplit("_", maxsplit=1)[1])
        return np.full((2, 3, 3), frame_value, dtype=np.uint8)

    monkeypatch.setattr("coloursorter.bench.replay_source.cv2.imread", _fake_imread)

    config = ReplayConfig(frame_period_s=0.04)

    run_a = _collect_replay_signature(ReplayFrameSource(tmp_path, config))
    run_b = _collect_replay_signature(ReplayFrameSource(tmp_path, config))

    assert run_a == run_b
    assert run_a == [
        (0, 0.0, 0),
        (1, 0.04, 1),
        (2, 0.08, 2),
    ]
