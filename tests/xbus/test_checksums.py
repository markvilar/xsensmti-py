"""
Unit tests for Xbus checksum validation functions.
"""

from __future__ import annotations

from xsensmti.xbus import (
    XbusMessageID,
    XbusFraming,
    XbusMessageHeader,
    XbusMessage,
    is_frame_checksum_valid,
)


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
        mid=XbusMessageID(frame[2]),
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
        mid=XbusMessageID(frame[2]),
        length=frame[3],
        ext_length=ext_length,
    )
    payload = frame[6:-1]
    checksum = frame[-1]
    return XbusMessage(header=header, payload=payload, checksum=checksum)


class TestIsFrameChecksumValid:
    def test_valid_standard_frame(self) -> None:
        frame = _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"")
        assert is_frame_checksum_valid(frame) is True

    def test_valid_standard_frame_with_payload(self) -> None:
        frame = _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x01\x02\x03")
        assert is_frame_checksum_valid(frame) is True

    def test_valid_extended_frame(self) -> None:
        frame = _make_extended_frame(0xFF, XbusMessageID.MTDATA2, b"\xab" * 300)
        assert is_frame_checksum_valid(frame) is True

    def test_invalid_when_checksum_byte_is_wrong(self) -> None:
        frame = bytearray(_make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x01"))
        frame[-1] ^= 0x01
        assert is_frame_checksum_valid(bytes(frame)) is False

    def test_invalid_when_payload_byte_is_corrupted(self) -> None:
        frame = bytearray(
            _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x01\x02")
        )
        frame[4] ^= 0xFF
        assert is_frame_checksum_valid(bytes(frame)) is False


class TestIsChecksumValid:
    def test_valid_standard_message(self) -> None:
        frame = _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x10\x20")
        message = _parse_standard_message(frame)
        assert message.is_checksum_valid() is True

    def test_valid_extended_message(self) -> None:
        frame = _make_extended_frame(0xFF, XbusMessageID.MTDATA2, b"\xab" * 300)
        message = _parse_extended_message(frame)
        assert message.is_checksum_valid() is True

    def test_invalid_when_checksum_field_is_wrong(self) -> None:
        frame = _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x01")
        message = _parse_standard_message(frame)
        tampered = XbusMessage(
            header=message.header,
            payload=message.payload,
            checksum=message.checksum ^ 0x01,
        )
        assert tampered.is_checksum_valid() is False

    def test_invalid_when_payload_byte_is_corrupted(self) -> None:
        frame = _make_standard_frame(0xFF, XbusMessageID.MTDATA2, b"\x01\x02")
        message = _parse_standard_message(frame)
        tampered = XbusMessage(
            header=message.header,
            payload=bytes([message.payload[0] ^ 0xFF]) + message.payload[1:],
            checksum=message.checksum,
        )
        assert tampered.is_checksum_valid() is False

    def test_returns_false_when_extended_header_has_no_ext_length(self) -> None:
        header = XbusMessageHeader(
            preamble=XbusFraming.PREAMBLE,
            bid=0xFF,
            mid=XbusMessageID.MTDATA2,
            length=XbusFraming.EXTLEN,
            ext_length=None,
        )
        message = XbusMessage(header=header, payload=b"", checksum=0x00)
        assert message.is_checksum_valid() is False
