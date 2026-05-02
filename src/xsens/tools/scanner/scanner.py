"""
Scanner for connected XSens MTi devices.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import serial
import serial.tools.list_ports
from loguru import logger
from serial.tools.list_ports_common import ListPortInfo

from xsens.xbus.datatypes import MessageID, XbusMessage

from ..exceptions import CommandTimeout, DeviceNotFound, UnexpectedResponse
from ..serial_io import open_serial_port, send_and_receive


@dataclass(frozen=True)
class ScanResult:
    """A single MTi device found during a port scan."""

    port: str
    device_id: int
    baud: int
    product_code: str


def scan_ports(
    baud: int = 115200,
    timeout: float = 2.0,
    usb_only: bool = False,
) -> list[ScanResult]:
    """
    Probe all available serial ports and return found MTi devices.
    """
    ports: Sequence[ListPortInfo] = serial.tools.list_ports.comports()

    if usb_only:
        ports = [p for p in ports if p.vid is not None]

    results: list[ScanResult] = []

    for port_info in ports:
        port_name: str = port_info.device
        ser: serial.Serial | None = None

        try:
            ser = open_serial_port(port_name, baud, read_timeout=0.1)
            ser.reset_input_buffer()

            send_and_receive(
                ser,
                MessageID.GOTOCONFIG,
                expected_mid=MessageID.GOTOCONFIG_ACK,
                timeout=timeout,
            )

            device_id_msg: XbusMessage = send_and_receive(
                ser,
                MessageID.REQ_DEVICE_ID,
                expected_mid=MessageID.DEVICE_ID,
                timeout=timeout,
            )
            device_id: int = int.from_bytes(device_id_msg.payload, "big")

            product_code: str = ""
            try:
                product_code_msg: XbusMessage = send_and_receive(
                    ser,
                    MessageID.REQ_PRODUCT_CODE,
                    expected_mid=MessageID.PRODUCT_CODE,
                    timeout=timeout,
                )
                product_code = product_code_msg.payload.rstrip(b"\x00").decode(
                    "ascii", errors="replace"
                )
            except (CommandTimeout, UnexpectedResponse):
                pass

            results.append(
                ScanResult(
                    port=port_name,
                    device_id=device_id,
                    baud=baud,
                    product_code=product_code,
                )
            )

        except (CommandTimeout, UnexpectedResponse, DeviceNotFound):
            logger.debug(f"{port_name}: no MTi device found")
        except (OSError, serial.SerialException) as exc:
            logger.debug(f"{port_name}: could not open port: {exc}")
        finally:
            if ser is not None:
                ser.close()

    return results
