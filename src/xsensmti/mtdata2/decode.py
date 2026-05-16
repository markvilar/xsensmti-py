"""
Helpers for decoding MTData2 packets from Xbus message payloads.
"""

from __future__ import annotations

from collections.abc import Iterator

from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
)

from .datatypes import OutputDataIdentifier
from .datatypes import OutputDataPacket
from .exceptions import NotMTData2Message
from .exceptions import TruncatedPacket


def decode_mtdata2_packets_from_message(message: XbusMessage) -> list[OutputDataPacket]:
    """
    Decode all MTData2 packets from an MTDATA2 XbusMessage.
    """
    return list(iter_mtdata2_packets_from_message(message))


def iter_mtdata2_packets_from_message(
    message: XbusMessage,
) -> Iterator[OutputDataPacket]:
    """
    Yield MTData2 packets parsed from an MTDATA2 XbusMessage payload.
    """
    if message.header.mid != XbusMessageID.MTDATA2:
        raise NotMTData2Message(
            f"expected MID {XbusMessageID.MTDATA2:#x}, got {message.header.mid:#x}"
        )
    yield from iter_mtdata2_packets_from_payload(message.payload)


def iter_mtdata2_packets_from_payload(payload: bytes) -> Iterator[OutputDataPacket]:
    """
    Yield MTData2 packets from a raw payload buffer.
    """
    offset: int = 0
    while offset + 3 <= len(payload):
        data_id: OutputDataIdentifier = OutputDataIdentifier(
            int.from_bytes(payload[offset : offset + 2], byteorder="big")
        )
        length: int = payload[offset + 2]
        offset += 3
        if offset + length > len(payload):
            raise TruncatedPacket(
                f"packet at offset {offset - 3} declares {length} bytes "
                f"but only {len(payload) - offset} remain"
            )
        data: bytes = payload[offset : offset + length]
        yield OutputDataPacket(data_id=data_id, length=length, data=data)
        offset += length
