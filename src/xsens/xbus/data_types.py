"""
Data types for Xbus headers, messages, and framing constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# NOTE: XSens defines an Xbus message as:
# Preamble | BID | MID | LEN | [LENext] | DATA | CHECKSUM


class XbusFraming(IntEnum):
    """Framing constants used by the Xbus wire format."""

    PREAMBLE = 0xFA
    EXTLEN = 0xFF


class PayloadLength(IntEnum):
    """Limits for standard and extended Xbus payload lengths."""

    MAX_STD = 0xFE
    MAX_EXT = 0x0800


@dataclass(frozen=True)
class XbusMessageHeaderPrefix:
    """Common 4-byte Xbus header prefix."""

    preamble: int
    bid: int
    mid: int
    length: int

    def is_extended_message(self) -> bool:
        """
        Return True if the prefix uses extended-length framing.
        """
        return self.length == XbusFraming.EXTLEN

    def is_standard_message(self) -> bool:
        """
        Return True if the prefix uses standard-length framing.
        """
        return not self.is_extended_message()


@dataclass(frozen=True)
class XbusMessageHeader:
    """
    Resolved Xbus message header.

    Attributes
    ----------
    preamble:       Fixed message preamble
    bid:            Bus ID
    mid:            Message ID
    length:         Payload length marker
    ext_length:     Extended payload length marker
    """

    preamble: int
    bid: int
    mid: int
    length: int
    ext_length: int | None = None

    @property
    def payload_length(self) -> int:
        """
        Return the payload length described by the header.
        """
        return self.ext_length if self.ext_length is not None else self.length

    @property
    def frame_length(self) -> int:
        """
        Return the total frame length described by the header.
        """
        if self.ext_length is None:
            return 1 + 1 + 1 + 1 + self.length + 1
        return 1 + 1 + 1 + 1 + 2 + self.ext_length + 1

    def is_extended_message(self) -> bool:
        """
        Return True if the header uses extended-length framing.
        """
        return self.length == XbusFraming.EXTLEN

    def is_standard_message(self) -> bool:
        """
        Return True if the header uses standard-length framing.
        """
        return not self.is_extended_message()


@dataclass(frozen=True)
class XbusMessage:
    """
    Parsed Xbus message with header, payload, and checksum.

    Attributes
    ----------
    header:     Xbus message header
    payload:    Payload or DATA field
    checksum:   Checksum for the message
    """

    header: XbusMessageHeader
    payload: bytes
    checksum: int
