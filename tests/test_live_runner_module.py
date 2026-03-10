from __future__ import annotations

from types import SimpleNamespace

import pytest

import coloursorter.runtime.live_runner as live_runner


class _TransportWithNoPing:
    def send(self, _command):
        return None


def test_build_live_transport_rejects_unsupported_kind() -> None:
    """Error path: unsupported transport kind raises ValueError."""
    runtime = SimpleNamespace(transport=SimpleNamespace(kind="unknown", serial_port="x", serial_baud=1, serial_timeout_s=0.1))
    with pytest.raises(ValueError, match="Unsupported transport kind"):
        live_runner.build_live_transport(runtime)


def test_startup_diagnostics_flags_missing_send_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boundary: startup diagnostics fail transport check when send_command is unavailable."""

    class _FrameSource:
        def open(self):
            return None

        def next_frame(self):
            return SimpleNamespace(image_bgr=live_runner.np.zeros((2, 2, 3), dtype=live_runner.np.uint8))

        def release(self):
            return None

    runtime = SimpleNamespace(
        detection=SimpleNamespace(
            active_camera_recipe="a",
            active_lighting_recipe="b",
            profiles=[SimpleNamespace(camera_recipe="a", lighting_recipe="b")],
            provider="model_stub",
            preprocess=SimpleNamespace(enable_normalization=True, target_luma=128.0, gray_world_strength=0.6),
        )
    )
    runner = live_runner.LiveRuntimeRunner.__new__(live_runner.LiveRuntimeRunner)
    runner._runtime_config = runtime
    runner._frame_source = _FrameSource()
    runner._detector = SimpleNamespace(provider_version="p", model_version="m", active_config_hash="h")
    runner._transport = _TransportWithNoPing()
    report = live_runner.LiveRuntimeRunner._run_startup_diagnostics(runner)
    assert report.transport_ping.passed is False
    assert "send_command_missing" in report.transport_ping.reason
