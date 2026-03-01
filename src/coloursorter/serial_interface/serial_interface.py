from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

FRAME_START = "<"
FRAME_END = ">"
FRAME_DELIMITER = "|"


class SerialInterfaceError(ValueError):
    """Base class for framing and packet validation failures."""


class FrameFormatError(SerialInterfaceError):
    """Raised when the frame does not match the expected <...> format."""


class PacketValidationError(SerialInterfaceError):
    """Raised when packet command or arguments are invalid."""


@dataclass(frozen=True)
class FramedPacket:
    command: str
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


def _validate_token(token: str, field_name: str) -> None:
    if not token:
        raise PacketValidationError(f"{field_name} cannot be empty")
    if any(ch in token for ch in (FRAME_DELIMITER, FRAME_START, FRAME_END)):
        raise PacketValidationError(f"{field_name} contains reserved framing characters")


def serialize_packet(command: str, args: Sequence[object] = ()) -> str:
    """Serialize command + args into <CMD|arg1|arg2> wire frame."""
    command_token = str(command).strip().upper()
    _validate_token(command_token, "command")

    arg_tokens: list[str] = []
    for index, arg in enumerate(args):
        token = str(arg).strip()
        _validate_token(token, f"arg[{index}]")
        arg_tokens.append(token)

    body = FRAME_DELIMITER.join((command_token, *arg_tokens))
    return f"{FRAME_START}{body}{FRAME_END}"


def parse_frame(frame: str) -> FramedPacket:
    """Parse <CMD|arg1|arg2> frame into command and positional args."""
    if len(frame) < 3:
        raise FrameFormatError("frame is too short")
    if not frame.startswith(FRAME_START) or not frame.endswith(FRAME_END):
        raise FrameFormatError("frame must start with '<' and end with '>'")

    body = frame[1:-1]
    if not body:
        raise FrameFormatError("frame body is empty")

    tokens = body.split(FRAME_DELIMITER)
    command = tokens[0].strip().upper()
    args = tuple(token.strip() for token in tokens[1:])

    _validate_token(command, "command")
    for index, arg in enumerate(args):
        _validate_token(arg, f"arg[{index}]")

    return FramedPacket(command=command, args=args)


def encode_packet_bytes(command: str, args: Sequence[object] = ()) -> bytes:
    return (serialize_packet(command, args) + "\n").encode("ascii")


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
    if status == "ACK":
        if len(token_list) == 1:
            return AckResponse(status="ACK")
        if len(token_list) != 5:
            raise PacketValidationError("ACK metadata must be mode|queue_depth|scheduler_state|queue_cleared")
        mode = token_list[1].strip().upper()
        if mode not in {"AUTO", "MANUAL", "SAFE"}:
            raise PacketValidationError("ACK mode must be AUTO, MANUAL, or SAFE")
        try:
            queue_depth = int(token_list[2])
        except ValueError as exc:
            raise PacketValidationError("ACK queue_depth must be an integer") from exc
        scheduler_state = token_list[3].strip().upper()
        raw_queue_cleared = token_list[4].strip().lower()
        if raw_queue_cleared not in {"true", "false"}:
            raise PacketValidationError("ACK queue_cleared must be true or false")
        return AckResponse(
            status="ACK",
            mode=mode,
            queue_depth=queue_depth,
            scheduler_state=scheduler_state,
            queue_cleared=raw_queue_cleared == "true",
        )
    if status != "NACK":
        raise PacketValidationError("response must start with ACK or NACK")

    if len(token_list) < 2:
        raise PacketValidationError("NACK requires nack_code")
    try:
        nack_code = int(token_list[1])
    except ValueError as exc:
        raise PacketValidationError("nack_code must be an integer") from exc
    if nack_code < 1 or nack_code > 8:
        raise PacketValidationError("nack_code must be in the OpenSpec range 1..8")

    detail = token_list[2] if len(token_list) > 2 else None
    return AckResponse(status="NACK", nack_code=nack_code, detail=detail)
