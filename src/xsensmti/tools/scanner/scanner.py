"""
Scanner for connected XSens MTi devices.
"""

from __future__ import annotations

import serial
import serial.tools.list_ports

from collections.abc import Sequence
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
)
from dataclasses import dataclass
from loguru import logger
from serial.tools.list_ports_common import ListPortInfo
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from xsensmti.port import MtiPortInfo
from xsensmti.serial import (
    open_serial_port,
    send_and_receive,
)
from xsensmti.exceptions import (
    CommandTimeout,
    DeviceNotFound,
    UnexpectedResponse,
)


@dataclass(frozen=True)
class ScanOptions:
    """Parameters controlling how a port scan is performed."""

    baud: int = 115200
    timeout: float = 2.0


@dataclass(frozen=True)
class MtiScanResult:
    """A detected MTi device with its connection parameters and queried identity."""

    port_info: MtiPortInfo
    device_id: int
    product_code: str


def scan_port(
    port: str,
    options: ScanOptions | None = None,
    vid: int | None = None,
    pid: int | None = None,
) -> MtiScanResult | None:
    """
    Probe a single serial port and return a ScanResult if an MTi device is found.

    Returns None when no device is detected or the port cannot be opened.
    """
    opts: ScanOptions = options or ScanOptions()
    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, opts.baud, read_timeout=0.1)
        ser.reset_input_buffer()

        send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.GOTOCONFIG),
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=opts.timeout,
        )

        device_id_msg: XbusMessage = send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.REQ_DEVICE_ID),
            expected_mid=XbusMessageID.DEVICE_ID,
            timeout=opts.timeout,
        )
        device_id: int = int.from_bytes(device_id_msg.payload, "big")

        product_code: str = ""
        try:
            product_code_msg: XbusMessage = send_and_receive(
                ser,
                build_xbus_command(XbusMessageID.REQ_PRODUCT_CODE),
                expected_mid=XbusMessageID.PRODUCT_CODE,
                timeout=opts.timeout,
            )
            product_code = product_code_msg.payload.rstrip(b"\x00").decode(
                "ascii", errors="replace"
            )
        except (CommandTimeout, UnexpectedResponse):
            pass

        return MtiScanResult(
            port_info=MtiPortInfo(port=port, baud=opts.baud, vid=vid, pid=pid),
            device_id=device_id,
            product_code=product_code,
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
) -> list[MtiScanResult]:
    """
    Probe all available serial ports and return found MTi devices.
    """
    ports: Sequence[ListPortInfo] = serial.tools.list_ports.comports()

    if usb_only:
        ports = [port for port in ports if port.vid is not None]

    opts: ScanOptions = ScanOptions(baud=baud, timeout=timeout)

    with ThreadPoolExecutor() as executor:
        futures: list[Future[MtiScanResult | None]] = [
            executor.submit(scan_port, port.device, opts, port.vid, port.pid)
            for port in ports
        ]

    return [result for future in futures if (result := future.result()) is not None]
