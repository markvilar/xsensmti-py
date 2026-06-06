"""
MtiSession — session facade for opening and managing an XSens MTi device.
"""

from __future__ import annotations

from types import TracebackType
from loguru import logger
from xsensmti.exceptions import DeviceNotFound
from xsensmti.port import MtiPortInfo
from .communicator import MtiDeviceCommunicator
from .datatypes import MtiDeviceDescriptor
from .device import MtiDevice
from .scanner import _probe_port


class MtiSession:
    def __init__(self, port_info: MtiPortInfo, timeout: float = 5.0) -> None:
        self._port_info: MtiPortInfo = port_info
        self._timeout: float = timeout
        self._communicator: MtiDeviceCommunicator | None = None
        self._device: MtiDevice | None = None

    def open(self) -> MtiDevice:
        descriptor: MtiDeviceDescriptor | None = _probe_port(
            self._port_info.port,
            self._port_info.baud,
            self._timeout,
            self._port_info.vid,
            self._port_info.pid,
        )
        if descriptor is None:
            raise DeviceNotFound(f"no MTi device found on {self._port_info.port}")

        communicator: MtiDeviceCommunicator = MtiDeviceCommunicator(
            descriptor, timeout=self._timeout
        )

        logger.info(
            f"{descriptor.port_info.port}: {descriptor.device_info.product_code or '(unknown)'}  "
            f"ID: {descriptor.device_info.device_id:#010x}  "
            f"FW: {descriptor.device_info.firmware_version}  HW: {descriptor.device_info.hardware_version}"
        )

        self._communicator = communicator
        self._device = MtiDevice(communicator=communicator, timeout=self._timeout)
        return self._device

    def close(self) -> None:
        if self._communicator is not None:
            self._communicator.close()
            self._communicator = None
        self._device = None

    def __enter__(self) -> MtiDevice:
        return self.open()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
