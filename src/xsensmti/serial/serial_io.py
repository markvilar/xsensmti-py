"""
Serial port helpers for sending and receiving Xbus messages.
"""

from __future__ import annotations

import time

import serial

from xsensmti.xbus.datatypes import XbusMessage, XbusMessageID
from xsensmti.xbus.decode import iter_xbus_messages_from_buffer
from xsensmti.xbus.encode import encode_xbus_message
from xsensmti.xbus.exceptions import (
    IncompletePayload,
    InvalidPayloadLength,
    InvalidXbusMessageID,
    MissingChecksum,
    MissingHeader,
)
from xsensmti.exceptions import CommandTimeout, UnexpectedResponse


def open_serial_port(
    port: str,
    baud: int = 115200,
    read_timeout: float = 0.1,
) -> serial.Serial:
    """
    Open a serial port with MTi-compatible 8N1 settings.

    The `read_timeout` is intentionally short (0.1 s) so that receive_message()
    can poll without blocking and enforce its own wall-clock deadline.
    Caller is responsible for closing the port.
    """
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=read_timeout,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )


def send_message(
    ser: serial.Serial,
    mid: XbusMessageID | int,
    payload: bytes = b"",
    bid: int = 0xFF,
) -> None:
    """Encode and write one Xbus frame to the serial port."""
    ser.write(encode_xbus_message(mid, payload, bid))


def receive_message(
    ser: serial.Serial,
    expected_mid: XbusMessageID,
    timeout: float = 2.0,
    chunk_size: int = 256,
) -> XbusMessage:
    """
    Read bytes from the serial port until an XbusMessage with expected_mid arrives.

    Accumulates bytes across reads so that partial frames are not lost.
    Raises CommandTimeout if the deadline passes without a matching message.
    Raises UnexpectedResponse if ERROR (0x42) or WARNING (0x43) arrives instead.
    """
    port: str = ser.port or ""
    deadline: float = time.monotonic() + timeout
    accumulator: bytearray = bytearray()

    while time.monotonic() < deadline:
        chunk: bytes = ser.read(chunk_size)
        if chunk:
            accumulator.extend(chunk)

        try:
            for message in iter_xbus_messages_from_buffer(accumulator):
                mid: XbusMessageID
                try:
                    mid = XbusMessageID(message.header.mid)
                except ValueError:
                    continue

                if mid == expected_mid:
                    return message

                if mid in (XbusMessageID.ERROR, XbusMessageID.WARNING):
                    raise UnexpectedResponse(expected=expected_mid, received=mid)
        except (
            InvalidXbusMessageID,
            InvalidPayloadLength,
            IncompletePayload,
            MissingHeader,
            MissingChecksum,
        ):
            pass

    raise CommandTimeout(port=port, mid_sent=expected_mid, timeout=timeout)


def send_and_receive(
    ser: serial.Serial,
    mid: XbusMessageID | int,
    payload: bytes = b"",
    expected_mid: XbusMessageID | None = None,
    timeout: float = 2.0,
    bid: int = 0xFF,
) -> XbusMessage:
    """
    Send an Xbus message and wait for its acknowledgement.

    If expected_mid is not given, derives it as mid + 1 (the standard ACK
    convention used throughout the Xbus protocol).
    """
    if expected_mid is None:
        expected_mid = XbusMessageID(int(mid) + 1)

    send_message(ser, mid, payload, bid)
    return receive_message(ser, expected_mid, timeout)
