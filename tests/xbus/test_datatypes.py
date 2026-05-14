"""
Unit tests for xbus datatype properties and methods.
"""

from __future__ import annotations

from xsensmti.xbus import (
    XbusMessageID,
    XbusFraming,
    XbusMessageHeader,
    XbusMessageHeaderPrefix,
)


def _make_standard_prefix(length: int = 0x00) -> XbusMessageHeaderPrefix:
    return XbusMessageHeaderPrefix(
        preamble=XbusFraming.PREAMBLE,
        bid=0xFF,
        mid=XbusMessageID.MTDATA2,
        length=length,
    )


def _make_standard_header(length: int = 0x00) -> XbusMessageHeader:
    return XbusMessageHeader(
        preamble=XbusFraming.PREAMBLE,
        bid=0xFF,
        mid=XbusMessageID.MTDATA2,
        length=length,
    )


def _make_extended_header(ext_length: int = 0x00) -> XbusMessageHeader:
    return XbusMessageHeader(
        preamble=XbusFraming.PREAMBLE,
        bid=0xFF,
        mid=XbusMessageID.MTDATA2,
        length=XbusFraming.EXTLEN,
        ext_length=ext_length,
    )


class TestXbusMessageHeaderPrefix:
    def test_standard_message_when_length_is_not_extlen(self) -> None:
        prefix = _make_standard_prefix(length=0x10)
        assert prefix.is_standard_message() is True

    def test_not_extended_message_when_length_is_not_extlen(self) -> None:
        prefix = _make_standard_prefix(length=0x10)
        assert prefix.is_extended_message() is False

    def test_extended_message_when_length_is_extlen(self) -> None:
        prefix = _make_standard_prefix(length=XbusFraming.EXTLEN)
        assert prefix.is_extended_message() is True

    def test_not_standard_message_when_length_is_extlen(self) -> None:
        prefix = _make_standard_prefix(length=XbusFraming.EXTLEN)
        assert prefix.is_standard_message() is False

    def test_standard_and_extended_are_mutually_exclusive(self) -> None:
        for length in [0x00, 0x10, XbusFraming.EXTLEN]:
            prefix = _make_standard_prefix(length=length)
            assert prefix.is_standard_message() != prefix.is_extended_message()


class TestXbusMessageHeaderStandard:
    def test_is_standard_message(self) -> None:
        assert _make_standard_header(length=0x05).is_standard_message() is True

    def test_is_not_extended_message(self) -> None:
        assert _make_standard_header(length=0x05).is_extended_message() is False

    def test_payload_length_equals_length_field(self) -> None:
        header = _make_standard_header(length=0x0A)
        assert header.payload_length == 0x0A

    def test_frame_length_zero_payload(self) -> None:
        # preamble(1) + bid(1) + mid(1) + len(1) + payload(0) + checksum(1) = 5
        assert _make_standard_header(length=0).frame_length == 5

    def test_frame_length_nonzero_payload(self) -> None:
        # preamble(1) + bid(1) + mid(1) + len(1) + payload(N) + checksum(1) = 4 + N + 1
        for n in [1, 10, 0xFE]:
            assert _make_standard_header(length=n).frame_length == 4 + n + 1


class TestXbusMessageHeaderExtended:
    def test_is_extended_message(self) -> None:
        assert _make_extended_header(ext_length=0x10).is_extended_message() is True

    def test_is_not_standard_message(self) -> None:
        assert _make_extended_header(ext_length=0x10).is_standard_message() is False

    def test_payload_length_equals_ext_length(self) -> None:
        header = _make_extended_header(ext_length=0x0200)
        assert header.payload_length == 0x0200

    def test_frame_length_zero_payload(self) -> None:
        # preamble(1) + bid(1) + mid(1) + 0xFF(1) + ext_hi(1) + ext_lo(1) + payload(0) + checksum(1) = 7
        assert _make_extended_header(ext_length=0).frame_length == 7

    def test_frame_length_nonzero_payload(self) -> None:
        # 6 + ext_length + 1
        for n in [1, 100, 0x0800]:
            assert _make_extended_header(ext_length=n).frame_length == 6 + n + 1
