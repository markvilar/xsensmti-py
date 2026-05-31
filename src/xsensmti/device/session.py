"""
MtiSession — session facade for opening and managing an XSens MTi device.
"""

from __future__ import annotations

from types import TracebackType
from loguru import logger
from xsensmti.port import MtiPortInfo
from xsensmti.serial import open_serial_port
from .communicator import MtiDeviceCommunicator
from .datatypes import MtiDeviceInfo
from .device import MtiDevice


class MtiSession:
    def __init__(self, port_info: MtiPortInfo, timeout: float = 5.0) -> None:
        self._port_info: MtiPortInfo = port_info
        self._timeout: float = timeout
        self._communicator: MtiDeviceCommunicator | None = None
        self._device: MtiDevice | None = None

    def open(self) -> MtiDevice:
        ser = open_serial_port(
            self._port_info.port,
            self._port_info.baud,
            read_timeout=0.1,
        )
        ser.reset_input_buffer()

        communicator: MtiDeviceCommunicator = MtiDeviceCommunicator(
            ser, timeout=self._timeout
        )
        communicator.goto_config()

        device_id: MtiDeviceInfo = MtiDeviceInfo(
            device_id=communicator.get_device_id(),
            product_code=communicator.get_product_code(),
            firmware_version=communicator.get_firmware_version(),
            hardware_version=communicator.get_hardware_version(),
        )

        logger.info(
            f"{self._port_info.port}: {device_id.product_code or '(unknown)'}  "
            f"ID: {device_id.device_id:#010x}  "
            f"FW: {device_id.firmware_version}  HW: {device_id.hardware_version}"
        )

        self._communicator = communicator
        self._device = MtiDevice(
            device_id=device_id,
            communicator=communicator,
            timeout=self._timeout,
        )
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
