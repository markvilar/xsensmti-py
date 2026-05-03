"""
Unit tests for Xbus message encoding.
"""

from __future__ import annotations

import pytest

from xsens.xbus.datatypes import MessageID, PayloadLength
from xsens.xbus.decode import (
    decode_xbus_messages_from_buffer,
    is_frame_checksum_valid,
)
from xsens.xbus.encode import encode_xbus_message


class TestEncodeKnownFrames:
    def test_gotoconfig(self) -> None:
        assert encode_xbus_message(MessageID.GOTOCONFIG) == bytes.fromhex("faff3000d1")

    def test_req_device_id(self) -> None:
        assert encode_xbus_message(MessageID.REQ_DEVICE_ID) == bytes.fromhex(
            "faff000001"
        )

    def test_gotomeasurement(self) -> None:
        assert encode_xbus_message(MessageID.GOTOMEASUREMENT) == bytes.fromhex(
            "faff1000f1"
        )


class TestEncodeChecksumValid:
    def test_empty_payload(self) -> None:
        frame = encode_xbus_message(MessageID.GOTOCONFIG)
        assert is_frame_checksum_valid(frame)

    def test_with_payload(self) -> None:
        frame = encode_xbus_message(
            MessageID.OUTPUT_CONFIGURATION, payload=b"\x10\x20\x00\x64"
        )
        assert is_frame_checksum_valid(frame)

    def test_extended_frame(self) -> None:
        frame = encode_xbus_message(MessageID.MTDATA2, payload=b"\xab" * 300)
        assert is_frame_checksum_valid(frame)


class TestEncodeRoundTrip:
    def test_standard_round_trip(self) -> None:
        payload = b"\x01\x02\x03\x04"
        frame = encode_xbus_message(MessageID.OUTPUT_CONFIGURATION, payload=payload)
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        assert messages[0].header.mid == MessageID.OUTPUT_CONFIGURATION
        assert messages[0].payload == payload

    def test_empty_payload_round_trip(self) -> None:
        frame = encode_xbus_message(MessageID.GOTOCONFIG)
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        assert messages[0].header.mid == MessageID.GOTOCONFIG
        assert messages[0].payload == b""

    def test_extended_round_trip(self) -> None:
        payload = bytes(range(256))
        frame = encode_xbus_message(MessageID.MTDATA2, payload=payload)
        messages = decode_xbus_messages_from_buffer(frame)
        assert len(messages) == 1
        assert messages[0].payload == payload


class TestEncodeFraming:
    def test_standard_framing_at_max(self) -> None:
        payload = b"\x00" * PayloadLength.MAX_STD
        frame = encode_xbus_message(MessageID.MTDATA2, payload=payload)
        assert frame[3] == PayloadLength.MAX_STD

    def test_extended_framing_above_max_std(self) -> None:
        payload = b"\x00" * (PayloadLength.MAX_STD + 1)
        frame = encode_xbus_message(MessageID.MTDATA2, payload=payload)
        assert frame[3] == 0xFF

    def test_custom_bid(self) -> None:
        frame = encode_xbus_message(MessageID.GOTOCONFIG, bid=0x01)
        assert frame[1] == 0x01

    def test_raises_when_payload_too_large(self) -> None:
        with pytest.raises(ValueError):
            encode_xbus_message(
                MessageID.MTDATA2, payload=b"\x00" * (PayloadLength.MAX_EXT + 1)
            )
