"""
Port scanning and probing for XSens MTi devices.
"""

from __future__ import annotations

import serial
import serial.tools.list_ports

from concurrent.futures import Future, ThreadPoolExecutor
from loguru import logger
from xsensmti.exceptions import CommandTimeout, DeviceNotFound, UnexpectedResponse
from xsensmti.device.port import MtiPortInfo
from xsensmti.serial import open_serial_port, send_and_receive
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .datatypes import (
    MtiDeviceID,
    MtiDeviceInfo,
    MtiProbeResult,
    MtiScanResult,
)


def scan_port(port: str, baud: int = 115200) -> MtiScanResult | None:
    """
    Look up a single serial port by path and return its OS-reported info.

    No serial port is opened. Returns None if the port is not listed by the OS.

    Arguments
    ---------
    port: Serial port path to look up (e.g. "/dev/ttyUSB0").
    baud: Baud rate to embed in the returned port info.

    Returns
    -------
    An MtiScanResult if the port is found, or None.
    """
    from serial.tools.list_ports_common import ListPortInfo

    port_info: ListPortInfo
    for port_info in serial.tools.list_ports.comports():
        if port_info.device == port:
            return MtiScanResult(
                port_info=MtiPortInfo(
                    port=port_info.device,
                    baud=baud,
                    vid=port_info.vid,
                    pid=port_info.pid,
                )
            )
    return None


def scan_ports(baud: int = 115200, usb_only: bool = False) -> list[MtiScanResult]:
    """
    Enumerate all serial ports reported by the OS.

    No serial ports are opened.

    Arguments
    ---------
    baud: Baud rate to embed in each returned port info.
    usb_only: When True, only include ports with a USB vendor ID.

    Returns
    -------
    A list of MtiScanResult, one per matching port.
    """
    from serial.tools.list_ports_common import ListPortInfo

    results: list[MtiScanResult] = []
    port_info: ListPortInfo
    for port_info in serial.tools.list_ports.comports():
        if usb_only and port_info.vid is None:
            continue
        results.append(
            MtiScanResult(
                port_info=MtiPortInfo(
                    port=port_info.device,
                    baud=baud,
                    vid=port_info.vid,
                    pid=port_info.pid,
                )
            )
        )
    return results


def probe_port(port_info: MtiPortInfo, timeout: float = 2.0) -> MtiProbeResult | None:
    """
    Probe a single serial port for an XSens MTi device.

    Opens the port, puts the device in Config State, requests its identity,
    then closes the port. Raises no exceptions on failure — returns None instead.

    Arguments
    ---------
    port_info: Connection parameters for the port to probe.
    timeout: Maximum seconds to wait for each Xbus response.

    Returns
    -------
    An MtiProbeResult if an MTi device responds, or None.
    """
    ser: serial.Serial | None = None
    try:
        ser = open_serial_port(port_info.port, port_info.baud, read_timeout=0.1)
        ser.reset_input_buffer()

        send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.GOTOCONFIG),
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=timeout,
        )

        device_info: MtiDeviceInfo = MtiDeviceInfo(
            device_id=_request_device_id(ser, timeout),
            product_code=_request_product_code(ser, timeout),
            firmware_version=_request_firmware_version(ser, timeout),
            hardware_version=_request_hardware_version(ser, timeout),
        )

        logger.debug(
            f"{port_info.port}: found {device_info.product_code or '(unknown)'}  "
            f"ID: {device_info.device_id:#010x}  "
            f"FW: {device_info.firmware_version}  HW: {device_info.hardware_version}"
        )

        return MtiProbeResult(port_info=port_info, device_info=device_info)

    except (CommandTimeout, UnexpectedResponse, DeviceNotFound):
        logger.debug(f"{port_info.port}: no MTi device found")
        return None
    except (OSError, serial.SerialException) as exception:
        logger.debug(f"{port_info.port}: could not open port: {exception}")
        return None
    finally:
        if ser is not None:
            ser.close()


def probe_ports(
    port_infos: list[MtiPortInfo],
    timeout: float = 2.0,
) -> list[MtiProbeResult]:
    """
    Probe multiple serial ports in parallel for XSens MTi devices.

    Each port is probed in a separate thread. Ports where no device responds
    are silently skipped.

    Arguments
    ---------
    port_infos: Connection parameters for the ports to probe.
    timeout: Maximum seconds to wait for each Xbus response per port.

    Returns
    -------
    A list of MtiProbeResult for each port where a device was found.
    """
    futures: list[Future[MtiProbeResult | None]] = []
    with ThreadPoolExecutor() as executor:
        port_info: MtiPortInfo
        for port_info in port_infos:
            future: Future[MtiProbeResult | None] = executor.submit(
                probe_port, port_info, timeout
            )
            futures.append(future)

    results: list[MtiProbeResult] = []
    for future in futures:
        result: MtiProbeResult | None = future.result()
        if result is not None:
            results.append(result)
    return results


def _request_device_id(ser: serial.Serial, timeout: float) -> MtiDeviceID:
    message: XbusMessage = send_and_receive(
        ser,
        build_xbus_command(XbusMessageID.REQ_DEVICE_ID),
        expected_mid=XbusMessageID.DEVICE_ID,
        timeout=timeout,
    )
    return int.from_bytes(message.payload, "big")


def _request_product_code(ser: serial.Serial, timeout: float) -> str:
    try:
        message: XbusMessage = send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.REQ_PRODUCT_CODE),
            expected_mid=XbusMessageID.PRODUCT_CODE,
            timeout=timeout,
        )
        return message.payload.rstrip(b"\x00").decode("ascii", errors="replace")
    except (CommandTimeout, UnexpectedResponse):
        return ""


def _request_firmware_version(ser: serial.Serial, timeout: float) -> str:
    try:
        message: XbusMessage = send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.REQ_FIRMWARE_REVISION),
            expected_mid=XbusMessageID.FIRMWARE_REVISION,
            timeout=timeout,
        )
        return f"{message.payload[0]}.{message.payload[1]}.{message.payload[2]}"
    except (CommandTimeout, UnexpectedResponse):
        return ""


def _request_hardware_version(ser: serial.Serial, timeout: float) -> str:
    try:
        message: XbusMessage = send_and_receive(
            ser,
            build_xbus_command(XbusMessageID.REQ_HARDWARE_VERSION),
            expected_mid=XbusMessageID.HARDWARE_VERSION,
            timeout=timeout,
        )
        return f"{message.payload[0]}.{message.payload[1]}"
    except (CommandTimeout, UnexpectedResponse):
        return ""
