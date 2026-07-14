"""
Port scanning and probing for XSens MTi devices.
"""

from __future__ import annotations

import serial
import serial.tools.list_ports

from concurrent.futures import Future, ThreadPoolExecutor
from loguru import logger
from xsensmti.exceptions import (
    CommandTimeout,
    DeviceNotFound,
    MtiDeviceError,
    UnexpectedResponse,
)
from xsensmti.device.datatypes import MtiPortInfo
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


# Candidate baud rates for discovery, in probe order. This is a discovery policy
# rather than a protocol constant: the default first, so the common case costs a
# single attempt, then the plausible rates, with the exotic ones last.
BAUD_RATES: tuple[int, ...] = (
    115200,
    921600,
    460800,
    230400,
    57600,
    38400,
    19200,
    9600,
    4800,
    76800,
    28800,
    14400,
    2000000,
    3500000,
    4000000,
)


def scan_port(port: str, baud: int = 115200) -> MtiScanResult | None:
    """
    Look up a single serial port by path and return its OS-reported info.

    No serial port is opened. Returns None if the port is not listed by the OS.

    Args:
        port: Serial port path to look up (e.g. "/dev/ttyUSB0").
        baud: Baud rate to embed in the returned port info.

    Returns:
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

    Args:
        baud: Baud rate to embed in each returned port info.
        usb_only: When True, only include ports with a USB vendor ID.

    Returns:
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


def discover_baudrate(port: str, timeout: float = 0.5) -> int | None:
    """
    Find a baud rate at which a device on a port responds.

    A device cannot be asked its baud rate without already communicating at that
    rate, so the candidate rates are probed in turn until one responds. Nothing
    is written to the device.

    On a serial link (RS-232/RS-422/RS-485, or a USB-to-serial converter) the
    rate returned is the device's configured baud rate, because no other rate
    will produce a response. On an MTi's native USB interface the link ignores
    the baud rate entirely and every candidate responds, so the first is
    returned; it is a rate the port can be opened at, not the device's stored
    setting. Use request_baudrate() for the stored setting, which applies to the
    device's serial interface.

    Args:
        port: Serial port path, e.g. '/dev/ttyUSB0'.
        timeout: Maximum seconds to wait for a response at each candidate rate.

    Returns:
        A baud rate in bps at which the device responds, or None if none did.
    """
    for baud in BAUD_RATES:
        port_info: MtiPortInfo = MtiPortInfo(port=port, baud=baud)
        if probe_port(port_info, timeout=timeout) is not None:
            logger.debug(f"{port}: device responded at {baud} baud")
            return baud
        logger.trace(f"{port}: no response at {baud} baud")
    return None


def probe_port(port_info: MtiPortInfo, timeout: float = 2.0) -> MtiProbeResult | None:
    """
    Probe a single serial port for an XSens MTi device.

    Opens the port, puts the device in Config State, requests its identity,
    then closes the port. Raises no exceptions on failure — returns None instead.

    Args:
        port_info: Connection parameters for the port to probe.
        timeout: Maximum seconds to wait for each Xbus response.

    Returns:
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

    except (CommandTimeout, UnexpectedResponse, DeviceNotFound, MtiDeviceError):
        logger.trace(f"{port_info.port}: no MTi device found")
        return None
    except (OSError, serial.SerialException) as exception:
        logger.trace(f"{port_info.port}: could not open port: {exception}")
        return None
    finally:
        if ser is not None:
            ser.close()


def probe_ports(
    port_infos: list[MtiPortInfo],
    timeout: float = 2.0,
    max_workers: int | None = None,
) -> list[MtiProbeResult]:
    """
    Probe multiple serial ports in parallel for XSens MTi devices.

    Each port is probed in a separate thread. Ports where no device responds
    are silently skipped.

    Args:
        port_infos: Connection parameters for the ports to probe.
        timeout: Maximum seconds to wait for each Xbus response per port.
        max_workers: Maximum number of threads to use. Defaults to one per port.

    Returns:
        A list of MtiProbeResult for each port where a device was found.
    """
    futures: list[Future[MtiProbeResult | None]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
