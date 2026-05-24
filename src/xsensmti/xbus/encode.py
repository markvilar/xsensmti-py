"""
Encoder for Xbus frames — the write-path counterpart to decode.py.
"""

from __future__ import annotations

from .datatypes import (
    XbusFraming,
    PayloadLength,
    XbusMessage,
    XbusMessageHeader,
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
    return build_xbus_message(bid, XbusMessageID(mid), payload).to_bytes()


def build_xbus_message(
    bid: int,
    mid: XbusMessageID,
    payload: bytes,
) -> XbusMessage:
    """
    Construct an XbusMessage with a computed checksum.

    Uses standard framing for payloads up to 254 bytes and extended framing
    for larger payloads. The checksum is computed identically to
    `encode_xbus_message`.

    Arguments
    ---------
    bid:        Bus ID.
    mid:        Message ID.
    payload:    Payload bytes.

    Returns
    -------
    An XbusMessage with a valid checksum.
    """
    if len(payload) > PayloadLength.MAX_EXT:
        raise ValueError(
            f"payload length {len(payload)} exceeds maximum {PayloadLength.MAX_EXT}"
        )

    extended: bool = len(payload) > PayloadLength.MAX_STD
    payload_length: int = len(payload)

    if extended:
        body: bytes = (
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
    else:
        body = bytes([bid, int(mid), payload_length]) + payload

    checksum: int = (-sum(body)) & 0xFF

    return XbusMessage(
        header=XbusMessageHeader(
            preamble=int(XbusFraming.PREAMBLE),
            bid=bid,
            mid=mid,
            length=int(XbusFraming.EXTLEN) if extended else payload_length,
            ext_length=payload_length if extended else None,
        ),
        payload=payload,
        checksum=checksum,
    )


def build_xbus_command(
    mid: XbusMessageID,
    payload: bytes = b"",
    bid: int = 0xFF,
) -> XbusMessage:
    """
    Construct an outbound command XbusMessage with a computed checksum.

    Convenience wrapper around `build_xbus_message` with the bus ID defaulting
    to 0xFF (master device), which is correct for all host-to-device commands.

    Arguments
    ---------
    mid:        Message ID of the command.
    payload:    Command payload bytes.
    bid:        Bus ID (default 0xFF for the master device).

    Returns
    -------
    An XbusMessage with a valid checksum, ready to pass to the communicator.
    """
    return build_xbus_message(bid, mid, payload)
