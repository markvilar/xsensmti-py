"""
MtiSession — session facade for opening and managing an XSens MTi device.
"""

from __future__ import annotations

import serial

from types import TracebackType
from loguru import logger
from xsensmti.port import MtiPortInfo
from xsensmti.serial import (
    goto_config_mode,
    open_serial_port,
    send_and_receive,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
)
from xsensmti.device import MtiDevice, MtiDeviceID


class MtiSession:
    def __init__(self, port_info: MtiPortInfo, timeout: float = 5.0) -> None:
        self._port_info: MtiPortInfo = port_info
        self._timeout: float = timeout
        self._device: MtiDevice | None = None

    def open(self) -> MtiDevice:
        ser: serial.Serial = open_serial_port(
            self._port_info.port,
            self._port_info.baud,
            read_timeout=0.1,
        )
        ser.reset_input_buffer()

        goto_config_mode(ser, self._timeout)

        firmware_version: str = self._query_firmware_version(ser)
        hardware_version: str = self._query_hardware_version(ser)

        device_id: MtiDeviceID = MtiDeviceID(
            device_id=self._port_info.device_id,
            product_code=self._port_info.product_code,
            firmware_version=firmware_version,
            hardware_version=hardware_version,
        )

        logger.info(
            f"{self._port_info.port}: firmware {device_id.firmware_version}, "
            f"hardware {device_id.hardware_version}"
        )

        self._device = MtiDevice(
            device_id=device_id,
            ser=ser,
            timeout=self._timeout,
        )
        return self._device

    def close(self) -> None:
        if self._device is not None:
            self._device.close()
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

    def _query_firmware_version(self, ser: serial.Serial) -> str:
        msg: XbusMessage = send_and_receive(
            ser,
            XbusMessageID.REQ_FIRMWARE_REVISION,
            expected_mid=XbusMessageID.FIRMWARE_REVISION,
            timeout=self._timeout,
        )
        major: int = msg.payload[0]
        minor: int = msg.payload[1]
        patch: int = msg.payload[2]
        return f"{major}.{minor}.{patch}"

    def _query_hardware_version(self, ser: serial.Serial) -> str:
        msg: XbusMessage = send_and_receive(
            ser,
            XbusMessageID.REQ_HARDWARE_VERSION,
            expected_mid=XbusMessageID.HARDWARE_VERSION,
            timeout=self._timeout,
        )
        major: int = msg.payload[0]
        minor: int = msg.payload[1]
        return f"{major}.{minor}"
