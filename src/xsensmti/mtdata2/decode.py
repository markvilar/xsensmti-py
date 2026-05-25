"""
Helpers for decoding MTData2 packets from Xbus message payloads.
"""

from __future__ import annotations

from collections.abc import Iterator

from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
)

from xsensmti.exceptions import UnexpectedXbusMessage

from .datatypes import MtData2Packet
from .datatypes import MtData2PacketID
from .exceptions import TruncatedPacket


def decode_mtdata2_packets_from_message(message: XbusMessage) -> list[MtData2Packet]:
    """
    Decode all MTData2 packets from an MTDATA2 XbusMessage.
    """
    return list(iter_mtdata2_packets_from_message(message))


def iter_mtdata2_packets_from_message(
    message: XbusMessage,
) -> Iterator[MtData2Packet]:
    """
    Yield MTData2 packets parsed from an MTDATA2 XbusMessage payload.
    """
    if message.header.mid != XbusMessageID.MTDATA2:
        raise UnexpectedXbusMessage(
            f"expected MID {XbusMessageID.MTDATA2:#x}, got {message.header.mid:#x}"
        )
    yield from iter_mtdata2_packets_from_payload(message.payload)


def iter_mtdata2_packets_from_payload(payload: bytes) -> Iterator[MtData2Packet]:
    """
    Yield MTData2 packets from a raw payload buffer.

    Packets whose XDI is not a known MtData2PacketID are silently skipped.
    """
    offset: int = 0
    while offset + 3 <= len(payload):
        packet_id: int = int.from_bytes(payload[offset : offset + 2], byteorder="big")
        length: int = payload[offset + 2]
        offset += 3
        if offset + length > len(payload):
            raise TruncatedPacket(
                f"packet at offset {offset - 3} declares {length} bytes "
                f"but only {len(payload) - offset} remain"
            )
        data: bytes = payload[offset : offset + length]
        offset += length

        if packet_id in MtData2PacketID:
            yield _parse_mtdata2_packet(packet_id, length, data)


def _parse_mtdata2_packet(
    packet_id: int,
    length: int,
    data: bytes,
) -> MtData2Packet:
    return MtData2Packet(data_id=MtData2PacketID(packet_id), length=length, data=data)
