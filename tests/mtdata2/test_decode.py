"""
Unit tests for MTData2 packet parsing.
"""

from __future__ import annotations

import pytest

from xsensmti.xbus import (
    XbusMessageID,
    decode_xbus_messages_from_buffer,
    encode_xbus_message,
)
from xsensmti.mtdata2 import (
    MtData2PacketID,
    TruncatedPacket,
    UnexpectedXbusMessage,
    decode_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_payload,
)


def _make_raw_packet(xdi: MtData2PacketID, data: bytes) -> bytes:
    return int(xdi).to_bytes(2, "big") + bytes([len(data)]) + data


def _make_mtdata2_message(payload: bytes):
    frame = encode_xbus_message(XbusMessageID.MTDATA2, payload=payload)
    return decode_xbus_messages_from_buffer(frame)[0]


class TestIterMtdata2PacketsFromPayload:
    def test_empty_payload_yields_no_packets(self) -> None:
        assert list(iter_mtdata2_packets_from_payload(b"")) == []

    def test_single_packet_fields_are_correct(self) -> None:
        data = b"\x00\x2a"
        payload = _make_raw_packet(MtData2PacketID.PACKET_COUNTER, data)
        packets = list(iter_mtdata2_packets_from_payload(payload))
        assert len(packets) == 1
        assert packets[0].data_id == MtData2PacketID.PACKET_COUNTER
        assert packets[0].length == 2
        assert packets[0].data == data

    def test_multiple_packets_all_yielded(self) -> None:
        payload = (
            _make_raw_packet(MtData2PacketID.PACKET_COUNTER, b"\x00\x01")
            + _make_raw_packet(MtData2PacketID.SAMPLE_TIME_FINE, b"\x00\x00\x00\x02")
            + _make_raw_packet(MtData2PacketID.STATUS_WORD, b"\x00\x00\x00\x00")
        )
        packets = list(iter_mtdata2_packets_from_payload(payload))
        assert len(packets) == 3
        assert packets[0].data_id == MtData2PacketID.PACKET_COUNTER
        assert packets[1].data_id == MtData2PacketID.SAMPLE_TIME_FINE
        assert packets[2].data_id == MtData2PacketID.STATUS_WORD

    def test_truncated_packet_raises(self) -> None:
        # Declares 4 bytes of data but only 2 are present.
        payload = (
            int(MtData2PacketID.PACKET_COUNTER).to_bytes(2, "big") + b"\x04\xab\xcd"
        )
        with pytest.raises(TruncatedPacket):
            list(iter_mtdata2_packets_from_payload(payload))

    def test_incomplete_header_at_end_is_ignored(self) -> None:
        # A valid packet followed by only 2 bytes — not enough for a header (needs 3).
        payload = (
            _make_raw_packet(MtData2PacketID.PACKET_COUNTER, b"\x00\x01") + b"\x10\x60"
        )
        packets = list(iter_mtdata2_packets_from_payload(payload))
        assert len(packets) == 1

    def test_unknown_xdi_is_skipped(self) -> None:
        unknown = b"\xff\xff" + b"\x02" + b"\x00\x00"
        payload = (
            _make_raw_packet(MtData2PacketID.PACKET_COUNTER, b"\x00\x01")
            + unknown
            + _make_raw_packet(MtData2PacketID.SAMPLE_TIME_FINE, b"\x00\x00\x00\x02")
        )
        packets = list(iter_mtdata2_packets_from_payload(payload))
        assert len(packets) == 2
        assert packets[0].data_id == MtData2PacketID.PACKET_COUNTER
        assert packets[1].data_id == MtData2PacketID.SAMPLE_TIME_FINE


class TestDecodeMtdata2PacketsFromMessage:
    def test_returns_list_of_all_packets(self) -> None:
        payload = _make_raw_packet(
            MtData2PacketID.PACKET_COUNTER, b"\x00\x01"
        ) + _make_raw_packet(MtData2PacketID.STATUS_WORD, b"\x00\x00\x00\x00")
        message = _make_mtdata2_message(payload)
        packets = decode_mtdata2_packets_from_message(message)
        assert isinstance(packets, list)
        assert len(packets) == 2

    def test_non_mtdata2_mid_raises(self) -> None:
        frame = encode_xbus_message(XbusMessageID.GOTOCONFIG)
        message = decode_xbus_messages_from_buffer(frame)[0]
        with pytest.raises(UnexpectedXbusMessage):
            decode_mtdata2_packets_from_message(message)


class TestIterMtdata2PacketsFromMessage:
    def test_yields_same_packets_as_decode_function(self) -> None:
        payload = _make_raw_packet(MtData2PacketID.PACKET_COUNTER, b"\x00\x05")
        message = _make_mtdata2_message(payload)
        from_iter = list(iter_mtdata2_packets_from_message(message))
        from_decode = decode_mtdata2_packets_from_message(message)
        assert from_iter == from_decode

    def test_non_mtdata2_mid_raises(self) -> None:
        frame = encode_xbus_message(XbusMessageID.GOTOCONFIG)
        message = decode_xbus_messages_from_buffer(frame)[0]
        with pytest.raises(UnexpectedXbusMessage):
            list(iter_mtdata2_packets_from_message(message))
