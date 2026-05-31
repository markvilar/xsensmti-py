"""
MtiDeviceScanner — discovers connected XSens MTi devices on serial ports.
"""

from __future__ import annotations

import serial
import serial.tools.list_ports
import threading

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from loguru import logger
from serial.tools.list_ports_common import ListPortInfo
from xsensmti.exceptions import CommandTimeout, DeviceNotFound, UnexpectedResponse
from xsensmti.port import MtiPortInfo
from xsensmti.serial import open_serial_port, send_and_receive
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .datatypes import MtiDeviceInfo


@dataclass(frozen=True)
class MtiScanResult:
    """
    A detected MTi device with its connection parameters and identity.

    Attributes
    ----------
    port_info: Serial port connection parameters.
    device_info: Device identity information queried during the scan.
    """

    port_info: MtiPortInfo
    device_info: MtiDeviceInfo


class MtiDeviceScanner:
    def __init__(self) -> None:
        self._results: dict[int, MtiScanResult] = dict()
        self._lock: threading.Lock = threading.Lock()

    def scan_port(
        self,
        port: str,
        baud: int = 115200,
        timeout: float = 2.0,
    ) -> MtiScanResult | None:
        """
        Probe a single serial port and update the cached results.

        If a device is found it is added to or updated in the cache. If no
        device responds, any existing cached entry for that port is removed.

        Arguments
        ---------
        port: Serial port path to probe.
        baud: Baud rate to use.
        timeout: Maximum seconds to wait for each Xbus response.

        Returns
        -------
        An MtiScanResult if an MTi device is found, or None.
        """
        vid: int | None = None
        pid: int | None = None
        port_info: ListPortInfo
        for port_info in serial.tools.list_ports.comports():
            if port_info.device == port:
                vid = port_info.vid
                pid = port_info.pid
                break

        result: MtiScanResult | None = _probe_port(port, baud, timeout, vid, pid)

        with self._lock:
            if result is not None:
                self._results[result.device_info.device_id] = result
            else:
                stale: list[int] = []
                device_id: int
                cached: MtiScanResult
                for device_id, cached in self._results.items():
                    if cached.port_info.port == port:
                        stale.append(device_id)
                for device_id in stale:
                    del self._results[device_id]

        return result

    def scan_ports(
        self,
        baud: int = 115200,
        timeout: float = 2.0,
        usb_only: bool = False,
    ) -> list[MtiScanResult]:
        """
        Probe all available serial ports in parallel and cache found devices.

        Replaces all results from the previous scan entirely.

        Arguments
        ---------
        baud: Baud rate to use for probing.
        timeout: Maximum seconds to wait for each Xbus response per port.
        usb_only: When True, only probe ports with a USB vendor ID.

        Returns
        -------
        A list of MtiScanResult for each detected MTi device.
        """
        all_ports: list[ListPortInfo] = list(serial.tools.list_ports.comports())

        if usb_only:
            usb_ports: list[ListPortInfo] = []
            port_info: ListPortInfo
            for port_info in all_ports:
                if port_info.vid is not None:
                    usb_ports.append(port_info)
            all_ports = usb_ports

        futures: list[Future[MtiScanResult | None]] = []
        with ThreadPoolExecutor() as executor:
            for port_info in all_ports:
                future: Future[MtiScanResult | None] = executor.submit(
                    _probe_port,
                    port_info.device,
                    baud,
                    timeout,
                    port_info.vid,
                    port_info.pid,
                )
                futures.append(future)

        scan_results: list[MtiScanResult] = []
        for future in futures:
            probe_result: MtiScanResult | None = future.result()
            if probe_result is not None:
                scan_results.append(probe_result)

        with self._lock:
            self._results = dict()
            scan_result: MtiScanResult
            for scan_result in scan_results:
                self._results[scan_result.device_info.device_id] = scan_result

        return scan_results

    def find(self, device_id: int) -> MtiScanResult | None:
        """Return the cached scan result for a device ID, or None."""
        with self._lock:
            return self._results.get(device_id)

    def results(self) -> list[MtiScanResult]:
        """Return a copy of all cached scan results."""
        with self._lock:
            return list(self._results.values())

    def device_ids(self) -> set[int]:
        """Return the set of device IDs found in the last scan."""
        with self._lock:
            return set(self._results.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)

    def __contains__(self, device_id: object) -> bool:
        with self._lock:
            return device_id in self._results


def _probe_port(
    port: str,
    baud: int = 115200,
    timeout: float = 2.0,
    vid: int | None = None,
    pid: int | None = None,
) -> MtiScanResult | None:
    """
    Probe a single serial port for an XSens MTi device.

    Arguments
    ---------
    port: Serial port path to probe.
    baud: Baud rate to use.
    timeout: Maximum seconds to wait for each Xbus response.
    vid: USB vendor ID, if known.
    pid: USB product ID, if known.

    Returns
    -------
    An MtiScanResult if an MTi device responds, or None.
    """
    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, baud, read_timeout=0.1)
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
            f"{port}: found {device_info.product_code or '(unknown)'}  "
            f"ID: {device_info.device_id:#010x}  "
            f"FW: {device_info.firmware_version}  HW: {device_info.hardware_version}"
        )

        return MtiScanResult(
            port_info=MtiPortInfo(port=port, baud=baud, vid=vid, pid=pid),
            device_info=device_info,
        )

    except (CommandTimeout, UnexpectedResponse, DeviceNotFound):
        logger.debug(f"{port}: no MTi device found")
        return None
    except (OSError, serial.SerialException) as exception:
        logger.debug(f"{port}: could not open port: {exception}")
        return None
    finally:
        if ser is not None:
            ser.close()


def _request_device_id(ser: serial.Serial, timeout: float) -> int:
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
        return f"{message.payload[0]}." f"{message.payload[1]}." f"{message.payload[2]}"
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
