"""
Data types for Xbus headers, messages, and framing constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# NOTE: XSens defines an Xbus message as:
# Preamble | BID | MID | LEN | [LENext] | DATA | CHECKSUM


class XbusMessageID(IntEnum):
    """
    Xbus message identifier (protocol MID) defining the type of message
    and how its payload should be interpreted.

    For request/set commands that share one MID (e.g. OUTPUT_CONFIGURATION),
    an empty payload means "request current value" and a non-empty payload
    means "set new value". The device always responds with the _ACK MID.
    """

    # Device identification
    REQ_DEVICE_ID = 0x00
    DEVICE_ID = 0x01
    REQ_PRODUCT_CODE = 0x1C
    PRODUCT_CODE = 0x1D
    REQ_HARDWARE_VERSION = 0x1E
    HARDWARE_VERSION = 0x1F
    REQ_FIRMWARE_REVISION = 0x12
    FIRMWARE_REVISION = 0x13

    # Device configuration (section 5.3.5)
    REQ_CONFIGURATION = 0x0C
    CONFIGURATION = (
        0x0D  # Device sends full config to host; also sent at startup if enabled
    )

    # State control
    GOTOMEASUREMENT = 0x10
    GOTOMEASUREMENT_ACK = 0x11
    RESTORE_FACTORY_DEFAULTS = 0x0E
    RESTORE_FACTORY_DEFAULTS_ACK = 0x0F
    GOTOCONFIG = 0x30
    GOTOCONFIG_ACK = 0x31
    WAKEUP = 0x3E
    WAKEUP_ACK = 0x3F
    RESET = 0x40
    RESET_ACK = 0x41

    # Error / warning
    ERROR = 0x42
    WARNING = 0x43

    # Communication settings
    SET_BAUDRATE = 0x18
    SET_BAUDRATE_ACK = 0x19

    # Output configuration — empty payload = request, non-empty = set
    OUTPUT_CONFIGURATION = 0xC0
    OUTPUT_CONFIGURATION_ACK = 0xC1

    # String output — empty payload = request, non-empty = set
    STRING_OUTPUT_TYPE = 0x8E
    STRING_OUTPUT_TYPE_ACK = 0x8F

    # Option flags — empty payload = request, non-empty = set
    OPTION_FLAGS = 0x48
    OPTION_FLAGS_ACK = 0x49

    # Filter profile — empty payload = request, non-empty = set
    FILTER_PROFILE = 0x64
    FILTER_PROFILE_ACK = 0x65

    # GNSS platform (MTi-700 / GNSS/INS) — empty payload = request, non-empty = set
    GNSS_PLATFORM = 0x76
    GNSS_PLATFORM_ACK = 0x77

    # Legacy data
    MTDATA = 0x32
    REQ_DATA = 0x34

    # MTData2
    MTDATA2 = 0x36


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
    mid: XbusMessageID
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
    mid: XbusMessageID
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

    @property
    def mid(self) -> XbusMessageID:
        return self.header.mid

    def to_bytes(self) -> bytes:
        """
        Serialize the message to a complete Xbus frame ready for transmission.

        Returns
        -------
        A bytes object containing the full wire-format frame: preamble, header,
        payload, and checksum.
        """
        if self.header.is_extended_message():
            ext_length: int = self.header.ext_length or 0
            body: bytes = (
                bytes(
                    [
                        self.header.bid,
                        int(self.header.mid),
                        int(XbusFraming.EXTLEN),
                        (ext_length >> 8) & 0xFF,
                        ext_length & 0xFF,
                    ]
                )
                + self.payload
            )
        else:
            body = (
                bytes([self.header.bid, int(self.header.mid), self.header.length])
                + self.payload
            )
        return bytes([int(XbusFraming.PREAMBLE)]) + body + bytes([self.checksum])

    def is_checksum_valid(self) -> bool:
        """
        Return True if the message checksum is valid.

        According to the Xbus protocol, the low byte of the sum of all bytes
        excluding the preamble (BID + MID + LEN + [EXT LEN] + DATA + CHECKSUM)
        must equal zero.
        """
        data: list[int] = [
            self.header.bid,
            int(self.header.mid),
            self.header.length,
        ]
        if self.header.is_extended_message():
            if self.header.ext_length is None:
                return False
            data.append((self.header.ext_length >> 8) & 0xFF)
            data.append(self.header.ext_length & 0xFF)
        data.extend(self.payload)
        data.append(self.checksum)
        return (sum(data) & 0xFF) == 0
