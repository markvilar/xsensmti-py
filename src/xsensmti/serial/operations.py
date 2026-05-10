"""
Higher-level device operations over serial for XSens MTi devices.
"""

from __future__ import annotations

import time

import serial

from loguru import logger

from xsensmti.xbus.datatypes import XbusMessageID
from xsensmti.xbus.decode import iter_xbus_messages_from_buffer
from xsensmti.xbus.exceptions import (
    IncompletePayload,
    InvalidPayloadLength,
    InvalidXbusMessageID,
    MissingChecksum,
    MissingHeader,
)
from xsensmti.exceptions import CommandTimeout

from .serial_io import send_and_receive, send_message

_RECOVERY_TIMEOUT: float = 5.0
_RECOVERY_INTERVAL: float = 0.1


def goto_config_mode(ser: serial.Serial, timeout: float) -> None:
    """
    Transition the device to config mode reliably.

    Fast path: send GOTOCONFIG and wait up to `timeout` seconds for ACK.
    Fallback: send RESET then retry GOTOCONFIG every 100 ms for up to
    _RECOVERY_TIMEOUT seconds. Devices typically become responsive ~1.7 s
    after RESET (see docs/debug/mti_goto_config_mode_not_responding.md).
    """
    try:
        send_and_receive(
            ser,
            XbusMessageID.GOTOCONFIG,
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=timeout,
        )
        return
    except CommandTimeout:
        logger.debug(f"{ser.port}: GOTOCONFIG timed out — sending RESET and retrying")

    port: str = ser.port or ""

    try:
        ser.reset_input_buffer()
        send_message(ser, XbusMessageID.RESET)
        ser.flush()
    except (serial.SerialException, OSError):
        pass

    buf: bytearray = bytearray()
    deadline: float = time.monotonic() + _RECOVERY_TIMEOUT

    while time.monotonic() < deadline:
        try:
            send_message(ser, XbusMessageID.GOTOCONFIG)
            ser.flush()
        except (serial.SerialException, OSError):
            pass

        chunk_end: float = time.monotonic() + _RECOVERY_INTERVAL
        while time.monotonic() < chunk_end:
            try:
                chunk: bytes = ser.read(256)
                if chunk:
                    buf.extend(chunk)
            except (serial.SerialException, OSError):
                pass

        try:
            for msg in iter_xbus_messages_from_buffer(buf):
                try:
                    mid: XbusMessageID = XbusMessageID(msg.header.mid)
                except ValueError:
                    continue
                if mid == XbusMessageID.GOTOCONFIG_ACK:
                    logger.debug(f"{port}: GOTOCONFIG_ACK received after RESET")
                    return
        except (
            IncompletePayload,
            InvalidXbusMessageID,
            InvalidPayloadLength,
            MissingChecksum,
            MissingHeader,
        ):
            pass

    raise CommandTimeout(
        port=port,
        mid_sent=XbusMessageID.GOTOCONFIG,
        timeout=timeout + _RECOVERY_TIMEOUT,
    )


def goto_measurement_mode(ser: serial.Serial, timeout: float) -> None:
    """Transition the device to measurement mode."""
    send_and_receive(
        ser,
        XbusMessageID.GOTOMEASUREMENT,
        expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
        timeout=timeout,
    )
