from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import parse_frame, serialize_packet


def _status(frame: str) -> str:
    return parse_frame(frame).command


def test_host_firmware_reset_and_recovery_flow() -> None:
    firmware = OpenSpecV3Host(max_queue_depth=2)

    assert _status(firmware.handle_frame(serialize_packet("HELLO", ("3.1", "SCHED;HEARTBEAT"), msg_id="1"))) == "ACK"
    assert _status(firmware.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))) == "ACK"
    assert _status(firmware.handle_frame(serialize_packet("SCHED", ("1", "10.0"), msg_id="3"))) == "ACK"
    assert _status(firmware.handle_frame(serialize_packet("RESET_QUEUE", (), msg_id="4"))) == "ACK"

    assert len(firmware.queue) == 0
    assert firmware.scheduler_state == "IDLE"

    assert _status(firmware.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="5"))) == "ACK"


def test_host_firmware_duplicate_message_returns_cached_ack() -> None:
    firmware = OpenSpecV3Host()

    firmware.handle_frame(serialize_packet("HELLO", ("3.1", "SCHED;HEARTBEAT;DEDUPE"), msg_id="10"))
    firmware.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="11"))

    first = firmware.handle_frame(serialize_packet("SCHED", ("2", "25.0"), msg_id="12"))
    duplicate = firmware.handle_frame(serialize_packet("SCHED", ("2", "25.0"), msg_id="12"))

    assert first == duplicate
    assert len(firmware.queue) == 1
