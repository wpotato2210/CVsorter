from __future__ import annotations

from dataclasses import dataclass
import zlib
from typing import Iterable, Sequence

from coloursorter.protocol.constants import (
    ACK_TOKEN,
    ALLOWED_MODES,
    ALLOWED_SCHEDULER_STATES,
    NACK_CODE_MAX,
    NACK_CODE_MIN,
    NACK_TOKEN,
    QUEUE_DEPTH_MIN,
)

FRAME_START = "<"
FRAME_END = ">"
FRAME_DELIMITER = "|"
PAYLOAD_DELIMITER = ","


class SerialInterfaceError(ValueError):
    """Base class for framing and packet validation failures."""


class FrameFormatError(SerialInterfaceError):
    """Raised when the frame does not match the expected <...> format."""


class PacketValidationError(SerialInterfaceError):
    """Raised when packet command or arguments are invalid."""


@dataclass(frozen=True)
class FramedPacket:
    msg_id: str
    command: str
    payload: str = ""
    crc: str = ""
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class AckResponse:
    status: str
    nack_code: int | None = None
    detail: str | None = None
    mode: str | None = None
    queue_depth: int | None = None
    scheduler_state: str | None = None
    queue_cleared: bool = False
    link_state: str | None = None


def _validate_token(token: str, field_name: str) -> None:
    if not token:
        raise PacketValidationError(f"{field_name} cannot be empty")
    if any(ch in token for ch in (FRAME_DELIMITER, FRAME_START, FRAME_END)):
        raise PacketValidationError(f"{field_name} contains reserved framing characters")


def _compute_crc(msg_id: str, command: str, payload: str) -> str:
    body = FRAME_DELIMITER.join((msg_id, command, payload))
    return f"{zlib.crc32(body.encode('ascii')) & 0xFFFFFFFF:08X}"


def serialize_packet(command: str, args: Sequence[object] = (), *, msg_id: str = "0") -> str:
    """Serialize command + args into <MSG_ID|CMD|payload|CRC> wire frame."""
    msg_id_token = str(msg_id).strip()
    _validate_token(msg_id_token, "msg_id")
    command_token = str(command).strip().upper()
    _validate_token(command_token, "command")

    arg_tokens: list[str] = []
    for index, arg in enumerate(args):
        token = str(arg).strip()
        _validate_token(token, f"arg[{index}]")
        arg_tokens.append(token)

    payload = PAYLOAD_DELIMITER.join(arg_tokens)
    crc = _compute_crc(msg_id_token, command_token, payload)
    body = FRAME_DELIMITER.join((msg_id_token, command_token, payload, crc))
    return f"{FRAME_START}{body}{FRAME_END}"


def parse_frame(frame: str) -> FramedPacket:
    """Parse <MSG_ID|CMD|payload|CRC> frame into command and positional args."""
    if len(frame) < 3:
        raise FrameFormatError("frame is too short")
    if not frame.startswith(FRAME_START) or not frame.endswith(FRAME_END):
        raise FrameFormatError("frame must start with '<' and end with '>'")

    body = frame[1:-1]
    if not body:
        raise FrameFormatError("frame body is empty")

    tokens = body.split(FRAME_DELIMITER)
    if len(tokens) != 4:
        raise FrameFormatError("frame must provide msg_id|command|payload|crc")
    msg_id = tokens[0].strip()
    command = tokens[1].strip().upper()
    payload = tokens[2].strip()
    crc = tokens[3].strip().upper()

    _validate_token(msg_id, "msg_id")
    _validate_token(command, "command")
    if payload:
        for token in payload.split(PAYLOAD_DELIMITER):
            _validate_token(token.strip(), "payload_token")
    expected_crc = _compute_crc(msg_id, command, payload)
    if crc != expected_crc:
        raise FrameFormatError("frame crc mismatch")
    args = tuple(token.strip() for token in payload.split(PAYLOAD_DELIMITER) if token.strip())

    return FramedPacket(msg_id=msg_id, command=command, payload=payload, crc=crc, args=args)


def encode_packet_bytes(command: str, args: Sequence[object] = (), *, msg_id: str = "0") -> bytes:
    return (serialize_packet(command, args, msg_id=msg_id) + "\n").encode("ascii")


def decode_packet_bytes(payload: bytes) -> FramedPacket:
    try:
        text = payload.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise FrameFormatError("payload is not valid ascii") from exc
    return parse_frame(text)


def parse_ack_tokens(tokens: Iterable[str]) -> AckResponse:
    token_list = [token.strip() for token in tokens]
    if not token_list:
        raise PacketValidationError("ACK/NACK token list is empty")

    status = token_list[0].upper()
    if status == ACK_TOKEN:
        if len(token_list) == 1:
            return AckResponse(status=ACK_TOKEN)
        if len(token_list) not in {5, 6}:
            raise PacketValidationError("ACK metadata must be mode|queue_depth|scheduler_state|queue_cleared|[link_state]")
        mode = token_list[1].strip().upper()
        if mode not in ALLOWED_MODES:
            raise PacketValidationError("ACK mode must be AUTO, MANUAL, or SAFE")
        try:
            queue_depth = int(token_list[2])
        except ValueError as exc:
            raise PacketValidationError("ACK queue_depth must be an integer") from exc
        if queue_depth < QUEUE_DEPTH_MIN:
            raise PacketValidationError(f"ACK queue_depth must be >= {QUEUE_DEPTH_MIN}")
        scheduler_state = token_list[3].strip().upper()
        if scheduler_state not in ALLOWED_SCHEDULER_STATES:
            raise PacketValidationError("ACK scheduler_state must be IDLE or ACTIVE")
        raw_queue_cleared = token_list[4].strip().lower()
        if raw_queue_cleared not in {"true", "false"}:
            raise PacketValidationError("ACK queue_cleared must be true or false")
        link_state = token_list[5].strip().upper() if len(token_list) == 6 else None
        return AckResponse(
            status=ACK_TOKEN,
            mode=mode,
            queue_depth=queue_depth,
            scheduler_state=scheduler_state,
            queue_cleared=raw_queue_cleared == "true",
            link_state=link_state,
        )
    if status != NACK_TOKEN:
        raise PacketValidationError("response must start with ACK or NACK")

    if len(token_list) < 2:
        raise PacketValidationError("NACK requires nack_code")
    try:
        nack_code = int(token_list[1])
    except ValueError as exc:
        raise PacketValidationError("nack_code must be an integer") from exc
    if nack_code < NACK_CODE_MIN or nack_code > NACK_CODE_MAX:
        raise PacketValidationError(f"nack_code must be in the OpenSpec range {NACK_CODE_MIN}..{NACK_CODE_MAX}")

    detail = token_list[2] if len(token_list) > 2 else None
    return AckResponse(status=NACK_TOKEN, nack_code=nack_code, detail=detail)
