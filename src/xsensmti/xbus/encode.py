"""
Encoder for Xbus frames — the write-path counterpart to decode.py.
"""

from __future__ import annotations

from .datatypes import (
    XbusFraming,
    PayloadLength,
    XbusMessageID,
)


def encode_xbus_message(
    mid: XbusMessageID | int,
    payload: bytes = b"",
    bid: int = 0xFF,
) -> bytes:
    """
    Encode a valid Xbus frame ready for transmission.

    Uses standard framing for payloads up to 254 bytes and extended framing
    for larger payloads. BID defaults to 0xFF (broadcast), which is correct
    for all host-to-device commands.
    """
    if len(payload) > PayloadLength.MAX_EXT:
        raise ValueError(
            f"payload length {len(payload)} exceeds maximum {PayloadLength.MAX_EXT}"
        )

    body: bytes
    if len(payload) <= PayloadLength.MAX_STD:
        body = bytes([bid, int(mid), len(payload)]) + payload
    else:
        payload_length: int = len(payload)
        body = (
            bytes(
                [
                    bid,
                    int(mid),
                    XbusFraming.EXTLEN,
                    (payload_length >> 8) & 0xFF,
                    payload_length & 0xFF,
                ]
            )
            + payload
        )

    checksum: int = (-sum(body)) & 0xFF
    return bytes([XbusFraming.PREAMBLE]) + body + bytes([checksum])
