"""
MtiSession — session facade for opening and managing an XSens MTi device.
"""

from __future__ import annotations

from types import TracebackType
from loguru import logger
from xsensmti.exceptions import DeviceNotFound
from xsensmti.device.port import MtiPortInfo
from .communicator import MtiDeviceCommunicator
from .datatypes import MtiProbeResult
from .device import MtiDevice
from .scanner import probe_port


class MtiSession:
    def __init__(self, port_info: MtiPortInfo, timeout: float = 5.0) -> None:
        self._port_info: MtiPortInfo = port_info
        self._timeout: float = timeout
        self._communicator: MtiDeviceCommunicator | None = None
        self._device: MtiDevice | None = None

    def open(self) -> MtiDevice:
        probe_result: MtiProbeResult | None = probe_port(self._port_info, self._timeout)
        if probe_result is None:
            raise DeviceNotFound(f"no MTi device found on {self._port_info.port}")

        communicator: MtiDeviceCommunicator = MtiDeviceCommunicator(
            port_info=probe_result.port_info,
            device_info=probe_result.device_info,
            timeout=self._timeout,
        )

        logger.info(
            f"{probe_result.port_info.port}: {probe_result.device_info.product_code or '(unknown)'}  "
            f"ID: {probe_result.device_info.device_id:#010x}  "
            f"FW: {probe_result.device_info.firmware_version}  HW: {probe_result.device_info.hardware_version}"
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
