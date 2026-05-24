"""
MtiDeviceCommunicator — owns the serial port and XbusStreamReader for a single MTi device.
"""

from __future__ import annotations

import serial

from collections.abc import Callable
from xsensmti.serial import (
    send_and_receive as serial_send_and_receive,
    send_message,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .xbus_reader import XbusStreamReader


class MtiDeviceCommunicator:
    def __init__(self, ser: serial.Serial, timeout: float = 5.0) -> None:
        self._ser: serial.Serial = ser
        self._timeout: float = timeout
        self._message_callback: Callable[[XbusMessage], None] | None = None
        self._error_callback: Callable[[Exception], None] | None = None
        self._reader: XbusStreamReader = XbusStreamReader(
            ser=self._ser,
            on_message=self._dispatch_message,
            on_error=self._dispatch_error,
        )

    @property
    def port(self) -> str:
        return str(self._ser.port)

    # --- Callback registration ---

    def set_message_callback(self, callback: Callable[[XbusMessage], None]) -> None:
        self._message_callback = callback

    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        self._error_callback = callback

    # --- Identity queries ---

    def get_device_id(self) -> int:
        message: XbusMessage = self.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_DEVICE_ID),
            expected_mid=XbusMessageID.DEVICE_ID,
        )
        return int.from_bytes(message.payload, "big")

    def get_product_code(self) -> str:
        message: XbusMessage = self.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_PRODUCT_CODE),
            expected_mid=XbusMessageID.PRODUCT_CODE,
        )
        return message.payload.rstrip(b"\x00").decode("ascii", errors="replace")

    def get_firmware_version(self) -> str:
        message: XbusMessage = self.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_FIRMWARE_REVISION),
            expected_mid=XbusMessageID.FIRMWARE_REVISION,
        )
        return f"{message.payload[0]}.{message.payload[1]}.{message.payload[2]}"

    def get_hardware_version(self) -> str:
        message: XbusMessage = self.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_HARDWARE_VERSION),
            expected_mid=XbusMessageID.HARDWARE_VERSION,
        )
        return f"{message.payload[0]}.{message.payload[1]}"

    # --- Communication ---

    def send(self, message: XbusMessage) -> None:
        send_message(self._ser, message)

    def send_and_receive(
        self,
        message: XbusMessage,
        expected_mid: XbusMessageID,
        timeout: float | None = None,
    ) -> XbusMessage:
        effective_timeout: float = timeout if timeout is not None else self._timeout
        return serial_send_and_receive(
            self._ser,
            message,
            expected_mid=expected_mid,
            timeout=effective_timeout,
        )

    # --- State transitions ---

    def goto_config(self) -> None:
        self._reader.stop()
        self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOCONFIG),
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
        )

    def goto_measurement(self) -> None:
        self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOMEASUREMENT),
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
        )
        self._reader.start()

    # --- Port management ---

    def flush(self) -> None:
        self._ser.reset_input_buffer()

    def close(self) -> None:
        self._reader.stop()
        self._ser.close()

    # --- Internal ---

    def _dispatch_message(self, message: XbusMessage) -> None:
        if self._message_callback is not None:
            self._message_callback(message)

    def _dispatch_error(self, exc: Exception) -> None:
        if self._error_callback is not None:
            self._error_callback(exc)
