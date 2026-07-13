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

    # Available filter profiles — read-only query
    AVAILABLE_FILTER_PROFILES = 0x62
    AVAILABLE_FILTER_PROFILES_ACK = 0x63

    # GNSS platform (MTi-700 / GNSS/INS) — empty payload = request, non-empty = set
    GNSS_PLATFORM = 0x76
    GNSS_PLATFORM_ACK = 0x77

    # Legacy data
    MTDATA = 0x32
    REQ_DATA = 0x34

    # MTData2
    MTDATA2 = 0x36


class XbusErrorCode(IntEnum):
    """
    Error codes carried in the payload of an Xbus ERROR message.

    These are Xbus protocol codes, not MTi-specific ones: they are a subset of
    the XsResultValue enum used across the Xsens device range. A device may send
    a code outside this enum, so callers should preserve unknown values rather
    than reject them.
    """

    INVALID_PERIOD = 0x03
    INVALID_MESSAGE = 0x04
    TIMER_OVERFLOW = 0x1E
    INVALID_BAUDRATE = 0x20
    INVALID_PARAMETER = 0x21
    DEVICE_ERROR = 0x28


class XbusBaudCode(IntEnum):
    """
    Baud rate codes carried in the payload of an Xbus SET_BAUDRATE message.

    These are Xbus protocol codes: the wire encoding of a baud rate, not the
    baud rate itself. The mapping is not ordered, so it cannot be computed —
    it is a lookup. A baud rate in bps is a plain int, as pyserial expects.

    BAUD_921600 and BAUD_921600_LEGACY encode the same rate; the former requires
    firmware 2.4.6 or later.
    """

    BAUD_460800 = 0x00
    BAUD_230400 = 0x01
    BAUD_115200 = 0x02
    BAUD_76800 = 0x03
    BAUD_57600 = 0x04
    BAUD_38400 = 0x05
    BAUD_28800 = 0x06
    BAUD_19200 = 0x07
    BAUD_14400 = 0x08
    BAUD_9600 = 0x09
    BAUD_921600 = 0x0A
    BAUD_4800 = 0x0B
    BAUD_2000000 = 0x0C
    BAUD_4000000 = 0x0D
    BAUD_3500000 = 0x0E
    BAUD_921600_LEGACY = 0x80

    def to_rate(self) -> int:
        """Return the baud rate in bps that this code encodes."""
        return _BAUD_CODE_RATES[self]


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


_BAUD_CODE_RATES: dict[XbusBaudCode, int] = {
    XbusBaudCode.BAUD_460800: 460800,
    XbusBaudCode.BAUD_230400: 230400,
    XbusBaudCode.BAUD_115200: 115200,
    XbusBaudCode.BAUD_76800: 76800,
    XbusBaudCode.BAUD_57600: 57600,
    XbusBaudCode.BAUD_38400: 38400,
    XbusBaudCode.BAUD_28800: 28800,
    XbusBaudCode.BAUD_19200: 19200,
    XbusBaudCode.BAUD_14400: 14400,
    XbusBaudCode.BAUD_9600: 9600,
    XbusBaudCode.BAUD_921600: 921600,
    XbusBaudCode.BAUD_4800: 4800,
    XbusBaudCode.BAUD_2000000: 2000000,
    XbusBaudCode.BAUD_4000000: 4000000,
    XbusBaudCode.BAUD_3500000: 3500000,
    XbusBaudCode.BAUD_921600_LEGACY: 921600,
}
