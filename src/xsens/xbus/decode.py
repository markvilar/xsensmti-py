"""
Helpers for decoding Xbus messages from binary buffers.
"""

from __future__ import annotations

from collections.abc import Iterator

from .datatypes import XbusFraming
from .datatypes import XbusMessageHeaderPrefix
from .datatypes import XbusMessageHeader
from .datatypes import XbusMessage
from .datatypes import MessageID

from .exceptions import MissingHeader
from .exceptions import MissingChecksum
from .exceptions import InvalidMessageID
from .exceptions import InvalidPayloadLength


def is_frame_checksum_valid(frame: bytes) -> bool:
    """
    Return True if a raw Xbus frame has a valid checksum.

    According to the Xbus protocol the following must hold:
     - The low byte of the sum of all bytes except the preamble must be zero.
    """
    return (sum(frame[1:]) & 0xFF) == 0


def is_message_checksum_valid(message: XbusMessage) -> bool:
    """
    Return True if a parsed Xbus message has a valid checksum.

    According to the Xbus protocol the following must hold:
     - The low byte of the sum of all bytes except the preamble must be zero.
    """
    header: XbusMessageHeader = message.header

    data: list[int] = [
        header.bid,
        header.mid,
        header.length,
    ]

    if header.is_extended_message():
        if header.ext_length is None:
            raise InvalidPayloadLength("extended message header is missing ext_length")
        data.append((header.ext_length >> 8) & 0xFF)
        data.append(header.ext_length & 0xFF)

    data.extend(message.payload)
    data.append(message.checksum)

    return (sum(data) & 0xFF) == 0


def decode_xbus_messages_from_buffer(buffer: bytes | bytearray) -> list[XbusMessage]:
    """
    Decode all Xbus messages found in a buffer.
    """
    return list(iter_xbus_messages_from_buffer(buffer))


def iter_xbus_messages_from_buffer(buffer: bytes | bytearray) -> Iterator[XbusMessage]:
    """
    Yield Xbus messages parsed from a buffer.
    """
    remaining: bytearray = bytearray(buffer)

    while True:
        try:
            start: int = remaining.index(XbusFraming.PREAMBLE)
        except ValueError:
            break

        if start > 0:
            del remaining[:start]

        if len(remaining) < 4:
            break

        # Parse header prefix, i.e. header without accounting for extended length
        prefix: XbusMessageHeaderPrefix = _parse_message_header_prefix(remaining)

        # Parse header based on type from header prefix
        header: XbusMessageHeader = _parse_message_header_from_prefix(prefix, remaining)

        # Select frame from the buffer
        frame: bytes = bytes(remaining[: header.frame_length])

        # Parse message from header and frame
        message: XbusMessage = _parse_message_from_header_and_frame(header, frame)

        # Validate message checksum
        if is_message_checksum_valid(message):
            yield message
            del remaining[: message.header.frame_length]
        else:
            del remaining[0]


def _parse_message_header_prefix(buffer: bytes | bytearray) -> XbusMessageHeaderPrefix:
    """
    Parse the common 4-byte Xbus header prefix.
    """
    if len(buffer) < 4:
        raise MissingHeader(f"not enough bytes for a valid header: {len(buffer)}")
    try:
        mid: MessageID = MessageID(buffer[2])
    except ValueError:
        raise InvalidMessageID(buffer[2])
    return XbusMessageHeaderPrefix(
        preamble=buffer[0],
        bid=buffer[1],
        mid=mid,
        length=buffer[3],
    )


def _parse_message_header_from_prefix(
    prefix: XbusMessageHeaderPrefix, buffer: bytes | bytearray
) -> XbusMessageHeader:
    """
    Resolve a full message header from a prefix and buffer, dispatching on standard vs. extended framing.
    """
    if prefix.is_standard_message():
        return _parse_message_header_standard(buffer)
    elif prefix.is_extended_message():
        return _parse_message_header_extended(buffer)
    else:
        raise NotImplementedError("invalid message type")


def _parse_message_header_standard(buffer: bytes | bytearray) -> XbusMessageHeader:
    """
    Parse a standard-length Xbus message header.
    """
    if len(buffer) < 4:
        raise MissingHeader(f"not enough bytes for a valid header: {len(buffer)}")
    try:
        mid: MessageID = MessageID(buffer[2])
    except ValueError:
        raise InvalidMessageID(buffer[2])
    return XbusMessageHeader(
        preamble=buffer[0],
        bid=buffer[1],
        mid=mid,
        length=buffer[3],
    )


def _parse_message_header_extended(buffer: bytes | bytearray) -> XbusMessageHeader:
    """
    Parse an extended-length Xbus message header.
    """
    if len(buffer) < 4:
        raise MissingHeader(f"not enough bytes for a valid header: {len(buffer)}")
    if len(buffer) < 6:
        raise InvalidPayloadLength(f"not enough bytes for payload field: {len(buffer)}")
    try:
        mid: MessageID = MessageID(buffer[2])
    except ValueError:
        raise InvalidMessageID(buffer[2])
    extended_length: int = int.from_bytes(buffer[4:6], byteorder="big")
    return XbusMessageHeader(
        preamble=buffer[0],
        bid=buffer[1],
        mid=mid,
        length=buffer[3],
        ext_length=extended_length,
    )


def _parse_message_from_header_and_frame(
    header: XbusMessageHeader, frame: bytes
) -> XbusMessage:
    """
    Parse an Xbus message from a resolved header and complete frame.
    """
    if len(frame) != header.frame_length:
        raise InvalidPayloadLength(
            f"frame length {len(frame)} does not match header frame length {header.frame_length}"
        )

    payload_start: int
    if header.is_standard_message():
        payload_start = 4
    elif header.is_extended_message():
        payload_start = 6
    else:
        raise InvalidPayloadLength("could not determine message type from header")

    if len(frame) < payload_start + 1:
        raise MissingChecksum(f"frame too short for payload and checksum: {len(frame)}")

    payload_end: int = len(frame) - 1
    payload: bytes = frame[payload_start:payload_end]
    checksum: int = frame[-1]

    if len(payload) != header.payload_length:
        raise InvalidPayloadLength(
            f"payload length {len(payload)} does not match header payload length {header.payload_length}"
        )

    return XbusMessage(
        header=header,
        payload=payload,
        checksum=checksum,
    )
