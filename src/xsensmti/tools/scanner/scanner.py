"""
Scanner for connected XSens MTi devices.
"""

from __future__ import annotations

import time
import serial
import serial.tools.list_ports

from collections.abc import Sequence
from dataclasses import dataclass

from loguru import logger
from serial.tools.list_ports_common import ListPortInfo
from xsensmti.xbus.datatypes import XbusMessage, XbusMessageID
from xsensmti.xbus.decode import iter_xbus_messages_from_buffer
from xsensmti.xbus.exceptions import (
    IncompletePayload,
    InvalidPayloadLength,
    InvalidXbusMessageID,
    MissingChecksum,
    MissingHeader,
)
from xsensmti.port import MtiPortInfo
from ..exceptions import CommandTimeout, DeviceNotFound, UnexpectedResponse
from ..serial_io import open_serial_port, send_and_receive, send_message

_RECOVERY_TIMEOUT: float = 5.0
_RECOVERY_INTERVAL: float = 0.1


def _goto_config_mode(ser: serial.Serial, timeout: float) -> None:
    """
    Put the device in config mode, with a RESET fallback for devices that are
    stuck in a bad persistent state and ignore GOTOCONFIG while streaming.

    Normal path: send GOTOCONFIG, wait up to `timeout` seconds for ACK.
    Fallback: send RESET, then retry GOTOCONFIG every 100 ms for up to
    _RECOVERY_TIMEOUT seconds.  Devices typically become responsive ~1.7 s
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

    ser.reset_input_buffer()
    send_message(ser, XbusMessageID.RESET)
    ser.flush()

    buf: bytearray = bytearray()
    deadline: float = time.monotonic() + _RECOVERY_TIMEOUT

    while time.monotonic() < deadline:
        send_message(ser, XbusMessageID.GOTOCONFIG)
        ser.flush()

        chunk_end: float = time.monotonic() + _RECOVERY_INTERVAL
        while time.monotonic() < chunk_end:
            chunk: bytes = ser.read(256)
            if chunk:
                buf.extend(chunk)

        try:
            for msg in iter_xbus_messages_from_buffer(buf):
                try:
                    mid: XbusMessageID = XbusMessageID(msg.header.mid)
                except ValueError:
                    continue
                if mid == XbusMessageID.GOTOCONFIG_ACK:
                    logger.debug(f"{ser.port}: GOTOCONFIG_ACK received after RESET")
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
        port=ser.port or "",
        mid_sent=XbusMessageID.GOTOCONFIG,
        timeout=timeout + _RECOVERY_TIMEOUT,
    )


@dataclass(frozen=True)
class ScanOptions:
    """Parameters controlling how a port scan is performed."""

    baud: int = 115200
    timeout: float = 2.0


def scan_port(
    port: str,
    options: ScanOptions | None = None,
    vid: int | None = None,
    pid: int | None = None,
) -> MtiPortInfo | None:
    """
    Probe a single serial port and return a ScanResult if an MTi device is found.

    Returns None when no device is detected or the port cannot be opened.
    """
    opts: ScanOptions = options or ScanOptions()
    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, opts.baud, read_timeout=0.1)
        ser.reset_input_buffer()

        _goto_config_mode(ser, opts.timeout)

        device_id_msg: XbusMessage = send_and_receive(
            ser,
            XbusMessageID.REQ_DEVICE_ID,
            expected_mid=XbusMessageID.DEVICE_ID,
            timeout=opts.timeout,
        )
        device_id: int = int.from_bytes(device_id_msg.payload, "big")

        product_code: str = ""
        try:
            product_code_msg: XbusMessage = send_and_receive(
                ser,
                XbusMessageID.REQ_PRODUCT_CODE,
                expected_mid=XbusMessageID.PRODUCT_CODE,
                timeout=opts.timeout,
            )
            product_code = product_code_msg.payload.rstrip(b"\x00").decode(
                "ascii", errors="replace"
            )
        except (CommandTimeout, UnexpectedResponse):
            pass

        return MtiPortInfo(
            port=port,
            baud=opts.baud,
            device_id=device_id,
            product_code=product_code,
            vid=vid,
            pid=pid,
        )

    except (CommandTimeout, UnexpectedResponse, DeviceNotFound):
        logger.debug(f"{port}: no MTi device found")
        return None
    except (OSError, serial.SerialException) as exc:
        logger.debug(f"{port}: could not open port: {exc}")
        return None
    finally:
        if ser is not None:
            ser.close()


def scan_ports(
    baud: int = 115200,
    timeout: float = 2.0,
    usb_only: bool = False,
) -> list[MtiPortInfo]:
    """
    Probe all available serial ports and return found MTi devices.
    """
    ports: Sequence[ListPortInfo] = serial.tools.list_ports.comports()

    if usb_only:
        ports = [p for p in ports if p.vid is not None]

    opts: ScanOptions = ScanOptions(baud=baud, timeout=timeout)

    results: list[MtiPortInfo] = []
    for port_info in ports:
        result: MtiPortInfo | None = scan_port(
            port_info.device,
            opts,
            vid=port_info.vid,
            pid=port_info.pid,
        )
        if result is not None:
            results.append(result)

    return results
