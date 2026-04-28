"""
Unit tests for Xbus checksum validation functions.
"""

from __future__ import annotations

import pytest

from xsens.xbus.datatypes import MessageID
from xsens.xbus.datatypes import XbusFraming
from xsens.xbus.datatypes import XbusMessageHeader
from xsens.xbus.datatypes import XbusMessage
from xsens.xbus.decode import is_frame_checksum_valid
from xsens.xbus.decode import is_message_checksum_valid
from xsens.xbus.exceptions import InvalidPayloadLength


def _make_standard_frame(bid: int, mid: int, payload: bytes) -> bytes:
    body = bytes([bid, mid, len(payload)]) + payload
    checksum = (-sum(body)) & 0xFF
    return bytes([XbusFraming.PREAMBLE]) + body + bytes([checksum])


def _make_extended_frame(bid: int, mid: int, payload: bytes) -> bytes:
    n = len(payload)
    body = bytes([bid, mid, XbusFraming.EXTLEN, (n >> 8) & 0xFF, n & 0xFF]) + payload
    checksum = (-sum(body)) & 0xFF
    return bytes([XbusFraming.PREAMBLE]) + body + bytes([checksum])


def _parse_standard_message(frame: bytes) -> XbusMessage:
    header = XbusMessageHeader(
        preamble=frame[0],
        bid=frame[1],
        mid=MessageID(frame[2]),
        length=frame[3],
    )
    payload = frame[4:-1]
    checksum = frame[-1]
    return XbusMessage(header=header, payload=payload, checksum=checksum)


def _parse_extended_message(frame: bytes) -> XbusMessage:
    ext_length = int.from_bytes(frame[4:6], byteorder="big")
    header = XbusMessageHeader(
        preamble=frame[0],
        bid=frame[1],
        mid=MessageID(frame[2]),
        length=frame[3],
        ext_length=ext_length,
    )
    payload = frame[6:-1]
    checksum = frame[-1]
    return XbusMessage(header=header, payload=payload, checksum=checksum)


class TestIsFrameChecksumValid:
    def test_valid_standard_frame(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"")
        assert is_frame_checksum_valid(frame) is True

    def test_valid_standard_frame_with_payload(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01\x02\x03")
        assert is_frame_checksum_valid(frame) is True

    def test_valid_extended_frame(self) -> None:
        frame = _make_extended_frame(0xFF, MessageID.MTDATA2, b"\xab" * 300)
        assert is_frame_checksum_valid(frame) is True

    def test_invalid_when_checksum_byte_is_wrong(self) -> None:
        frame = bytearray(_make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01"))
        frame[-1] ^= 0x01
        assert is_frame_checksum_valid(bytes(frame)) is False

    def test_invalid_when_payload_byte_is_corrupted(self) -> None:
        frame = bytearray(_make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01\x02"))
        frame[4] ^= 0xFF
        assert is_frame_checksum_valid(bytes(frame)) is False


class TestIsMessageChecksumValid:
    def test_valid_standard_message(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x10\x20")
        message = _parse_standard_message(frame)
        assert is_message_checksum_valid(message) is True

    def test_valid_extended_message(self) -> None:
        frame = _make_extended_frame(0xFF, MessageID.MTDATA2, b"\xab" * 300)
        message = _parse_extended_message(frame)
        assert is_message_checksum_valid(message) is True

    def test_invalid_when_checksum_field_is_wrong(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01")
        message = _parse_standard_message(frame)
        tampered = XbusMessage(
            header=message.header,
            payload=message.payload,
            checksum=message.checksum ^ 0x01,
        )
        assert is_message_checksum_valid(tampered) is False

    def test_invalid_when_payload_byte_is_corrupted(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01\x02")
        message = _parse_standard_message(frame)
        tampered = XbusMessage(
            header=message.header,
            payload=bytes([message.payload[0] ^ 0xFF]) + message.payload[1:],
            checksum=message.checksum,
        )
        assert is_message_checksum_valid(tampered) is False

    def test_raises_when_extended_header_has_no_ext_length(self) -> None:
        header = XbusMessageHeader(
            preamble=XbusFraming.PREAMBLE,
            bid=0xFF,
            mid=MessageID.MTDATA2,
            length=XbusFraming.EXTLEN,
            ext_length=None,
        )
        message = XbusMessage(header=header, payload=b"", checksum=0x00)
        with pytest.raises(InvalidPayloadLength):
            is_message_checksum_valid(message)
