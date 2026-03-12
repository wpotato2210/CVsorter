from __future__ import annotations

from dataclasses import dataclass

import pytest

from coloursorter.runtime.live_runner import FrameFreshnessGuard, STALE_FRAME_ERROR_MESSAGE


@dataclass(frozen=True)
class Frame:
    timestamp: float
    data: bytes


def test_frames_advance_normally() -> None:
    guard = FrameFreshnessGuard()

    frame1 = Frame(timestamp=1.0, data=b"a")
    frame2 = Frame(timestamp=2.0, data=b"b")

    guard.check(frame_timestamp_s=frame1.timestamp, frame_image_bgr=frame1.data)
    guard.check(frame_timestamp_s=frame2.timestamp, frame_image_bgr=frame2.data)


def test_timestamp_stall_detected() -> None:
    guard = FrameFreshnessGuard()

    frame1 = Frame(timestamp=1.0, data=b"a")
    frame2 = Frame(timestamp=1.0, data=b"b")

    guard.check(frame_timestamp_s=frame1.timestamp, frame_image_bgr=frame1.data)

    with pytest.raises(RuntimeError) as err:
        guard.check(frame_timestamp_s=frame2.timestamp, frame_image_bgr=frame2.data)

    assert "STALE_FRAME_DETECTED" in str(err.value)


def test_repeated_frame_detection() -> None:
    guard = FrameFreshnessGuard(max_repeats=2)

    frame = Frame(timestamp=1.0, data=b"x")
    frame2 = Frame(timestamp=2.0, data=b"x")
    frame3 = Frame(timestamp=3.0, data=b"x")
    frame4 = Frame(timestamp=4.0, data=b"x")

    guard.check(frame_timestamp_s=frame.timestamp, frame_image_bgr=frame.data)
    guard.check(frame_timestamp_s=frame2.timestamp, frame_image_bgr=frame2.data)
    guard.check(frame_timestamp_s=frame3.timestamp, frame_image_bgr=frame3.data)

    with pytest.raises(RuntimeError):
        guard.check(frame_timestamp_s=frame4.timestamp, frame_image_bgr=frame4.data)


def test_stale_frame_error_message_deterministic() -> None:
    guard = FrameFreshnessGuard()

    frame1 = Frame(timestamp=1.0, data=b"x")
    frame2 = Frame(timestamp=1.0, data=b"x")

    guard.check(frame_timestamp_s=frame1.timestamp, frame_image_bgr=frame1.data)

    with pytest.raises(RuntimeError) as err:
        guard.check(frame_timestamp_s=frame2.timestamp, frame_image_bgr=frame2.data)

    assert str(err.value) == STALE_FRAME_ERROR_MESSAGE


def test_capture_interval_timeout_detected() -> None:
    guard = FrameFreshnessGuard(frame_timeout_ms=100.0)
    guard.check(frame_timestamp_s=1.0, frame_image_bgr=b"a")

    with pytest.raises(RuntimeError, match="STALE_FRAME_DETECTED"):
        guard.check(frame_timestamp_s=1.11, frame_image_bgr=b"b")
