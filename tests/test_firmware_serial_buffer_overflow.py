from coloursorter.firmware import FirmwareSerialRxBuffer


def test_serial_buffer_overflow_counts_dropped_bytes() -> None:
    buffer = FirmwareSerialRxBuffer(capacity=8)

    buffer.push_stream("ABCDEFGHIJK")

    assert buffer.overflow_count == 3
    assert buffer.pop_frame() is None


def test_serial_buffer_recovers_after_overflow_on_newline_flush() -> None:
    buffer = FirmwareSerialRxBuffer(capacity=8)

    buffer.push_stream("ABCDEFGH")
    buffer.push_stream("\n")

    assert buffer.overflow_count == 1
    assert buffer.pop_frame() is None

    buffer = FirmwareSerialRxBuffer(capacity=16)
    buffer.push_stream("HELLO\n")
    assert buffer.pop_frame() == "HELLO"
