"""
Unit tests for Xbus message decoding from binary buffers.
"""

from __future__ import annotations

import pytest

from xsens.xbus.datatypes import MessageID
from xsens.xbus.datatypes import XbusFraming
from xsens.xbus.decode import decode_xbus_messages_from_buffer
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


class TestDecodeXbusMessagesFromBuffer:
    def test_empty_buffer_yields_no_messages(self) -> None:
        assert decode_xbus_messages_from_buffer(b"") == []

    def test_buffer_with_no_preamble_yields_no_messages(self) -> None:
        assert decode_xbus_messages_from_buffer(b"\x00\x01\x02\x03") == []

    def test_single_standard_message_no_payload(self) -> None:
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"")
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.header.bid == 0xFF
        assert msg.header.mid == MessageID.MTDATA2
        assert msg.payload == b""

    def test_single_standard_message_with_payload(self) -> None:
        payload = b"\x01\x02\x03"
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, payload)
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        assert messages[0].payload == payload

    def test_single_extended_message(self) -> None:
        payload = b"\xab" * 300
        frame = _make_extended_frame(0xFF, MessageID.MTDATA2, payload)
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.header.ext_length == 300
        assert msg.payload == payload

    def test_multiple_messages_all_yielded(self) -> None:
        frames = (
            _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01")
            + _make_standard_frame(0xFF, MessageID.GOTOCONFIG, b"")
            + _make_standard_frame(0xFF, MessageID.DEVICE_ID, b"\xde\xad")
        )
        messages = decode_xbus_messages_from_buffer(frames)
        assert len(messages) == 3
        assert messages[0].header.mid == MessageID.MTDATA2
        assert messages[1].header.mid == MessageID.GOTOCONFIG
        assert messages[2].header.mid == MessageID.DEVICE_ID

    def test_leading_garbage_is_skipped(self) -> None:
        garbage = b"\x00\x11\x22\x33"
        frame = _make_standard_frame(0xFF, MessageID.MTDATA2, b"\xab")
        messages = decode_xbus_messages_from_buffer(garbage + frame)
        assert len(messages) == 1
        assert messages[0].payload == b"\xab"

    def test_accepts_bytearray_input(self) -> None:
        frame = bytearray(_make_standard_frame(0xFF, MessageID.MTDATA2, b""))
        assert len(decode_xbus_messages_from_buffer(frame)) == 1

    def test_bad_checksum_message_is_not_yielded(self) -> None:
        frame = bytearray(_make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01"))
        frame[-1] ^= 0x01
        assert decode_xbus_messages_from_buffer(bytes(frame)) == []

    def test_bad_checksum_frame_followed_by_valid_frame(self) -> None:
        # Corrupt the checksum of the first frame; the second must still be decoded.
        # Payload bytes must not contain 0xFA to avoid a spurious preamble match.
        corrupted = bytearray(
            _make_standard_frame(0xFF, MessageID.MTDATA2, b"\x01\x02\x03")
        )
        corrupted[-1] ^= 0x01
        valid = _make_standard_frame(0xFF, MessageID.GOTOCONFIG, b"")
        messages = decode_xbus_messages_from_buffer(bytes(corrupted) + valid)
        assert len(messages) == 1
        assert messages[0].header.mid == MessageID.GOTOCONFIG

    def test_unknown_mid_raises_value_error(self) -> None:
        # 0x99 is not a valid MessageID — MessageID(0x99) raises ValueError
        raw = bytes([XbusFraming.PREAMBLE, 0xFF, 0x99, 0x00, 0x67])
        with pytest.raises(ValueError):
            decode_xbus_messages_from_buffer(raw)

    def test_truncated_frame_raises_invalid_payload_length(self) -> None:
        # Build a valid header that declares 10 payload bytes, but supply none.
        body = bytes([0xFF, MessageID.MTDATA2, 0x0A])
        truncated = bytes([XbusFraming.PREAMBLE]) + body
        with pytest.raises(InvalidPayloadLength):
            decode_xbus_messages_from_buffer(truncated)
