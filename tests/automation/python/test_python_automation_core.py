from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from coloursorter.bench.live_source import LiveConfig, LiveFrameSource
from coloursorter.bench.serial_transport import SerialMcuTransport, SerialTransportConfig
from coloursorter.config.runtime import RuntimeConfig
from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import encode_packet_bytes, parse_frame


class _MockStat:
    def __init__(self, size: int) -> None:
        self.st_size = size


class _FakeVideoCapture:
    def __init__(self, camera_index: int) -> None:
        self._opened = camera_index == 0
        self._released = False
        self._frame = np.full((4, 4, 3), 17, dtype=np.uint8)

    def isOpened(self) -> bool:
        return self._opened

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._released:
            return False, None
        return True, self._frame.copy()

    def release(self) -> None:
        self._released = True


class _LoopbackSerial:
    def __init__(self, host: OpenSpecV3Host, mode: str = "ok") -> None:
        self._host = host
        self._mode = mode
        self._last_payload: bytes = b""

    def write(self, payload: bytes) -> int:
        self._last_payload = payload
        return len(payload)

    def readline(self) -> bytes:
        if self._mode == "timeout":
            return b""
        if self._mode == "malformed":
            return b"<BROKEN|FRAME>\n"
        request_frame = self._last_payload.decode("ascii").strip()
        response_frame = self._host.handle_frame(request_frame)
        return (response_frame + "\n").encode("ascii")

    def close(self) -> None:
        return None


def _frame(command: str, args: list[str], msg_id: str) -> str:
    return encode_packet_bytes(command, args, msg_id=msg_id).decode("ascii").strip()


def _load_dataset() -> dict[str, object]:
    return json.loads(Path("test_data/protocol_frames.json").read_text(encoding="utf-8"))


def test_runtime_config_load_startup_with_filesystem_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    startup_yaml = Path("test_data/runtime_config_startup.yaml").read_text(encoding="utf-8")

    monkeypatch.setattr(Path, "stat", lambda self: _MockStat(len(startup_yaml.encode("utf-8"))))
    monkeypatch.setattr(Path, "read_text", lambda self, encoding="utf-8": startup_yaml)

    config = RuntimeConfig.load_startup("/mock/startup.yaml")

    assert config.motion_mode == "FOLLOW_BELT"
    assert config.transport.kind == "mock"
    assert config.transport.base_round_trip_ms == pytest.approx(2.0, abs=1e-9)


def test_live_frame_source_with_mock_camera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("coloursorter.bench.live_source.cv2.VideoCapture", _FakeVideoCapture)

    source = LiveFrameSource(LiveConfig(camera_index=0, frame_period_s=0.05))
    source.open()
    frame = source.next_frame()
    source.release()

    assert frame is not None
    assert frame.frame_id == 0
    assert frame.timestamp_s == pytest.approx(0.0, abs=1e-12)
    assert frame.image_bgr.shape == (4, 4, 3)


def test_host_protocol_encode_decode_and_malformed_packet() -> None:
    dataset = _load_dataset()
    hello = dataset["hello"]
    heartbeat = dataset["heartbeat"]
    sched = dataset["sched"]

    host = OpenSpecV3Host(max_queue_depth=2)

    hello_resp = host.handle_frame(_frame(hello["command"], hello["args"], hello["msg_id"]))
    assert parse_frame(hello_resp).command == "ACK"

    heartbeat_resp = host.handle_frame(_frame(heartbeat["command"], heartbeat["args"], heartbeat["msg_id"]))
    assert parse_frame(heartbeat_resp).command == "ACK"

    sched_resp = host.handle_frame(_frame(sched["command"], sched["args"], sched["msg_id"]))
    sched_packet = parse_frame(sched_resp)
    assert sched_packet.command == "ACK"
    assert sched_packet.args[1] == "1"

    malformed_resp = host.handle_frame(dataset["bad_crc_frame"])
    malformed_packet = parse_frame(malformed_resp)
    assert malformed_packet.command == "NACK"


def test_serial_transport_loopback_and_timeout() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    config = SerialTransportConfig(port="mock", baud=115200, timeout_s=0.001, max_retries=0)

    ok_transport = SerialMcuTransport(config, serial_factory=lambda **_: _LoopbackSerial(host, mode="ok"))
    response = ok_transport.send(ScheduledCommand(lane=1, position_mm=123.456))
    ok_transport.close()

    assert response.ack_code.value == "ACK"
    assert response.round_trip_ms >= 0.0

    timeout_transport = SerialMcuTransport(config, serial_factory=lambda **_: _LoopbackSerial(host, mode="timeout"))
    with pytest.raises(Exception):
        timeout_transport.send(ScheduledCommand(lane=1, position_mm=120.0))


def test_seeded_deterministic_inputs() -> None:
    rng_a = np.random.default_rng(seed=12345)
    rng_b = np.random.default_rng(seed=12345)
    sample_a = rng_a.normal(loc=0.0, scale=1.0, size=32)
    sample_b = rng_b.normal(loc=0.0, scale=1.0, size=32)
    assert np.allclose(sample_a, sample_b, atol=1e-12)
