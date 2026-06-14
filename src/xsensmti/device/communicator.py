"""
MtiDeviceCommunicator — owns the serial port and XbusStreamReader for a single MTi device.
"""

from __future__ import annotations

import serial

from collections.abc import Callable
from xsensmti.device.datatypes import MtiPortInfo
from xsensmti.serial import (
    open_serial_port,
    send_and_receive as serial_send_and_receive,
    send_message,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .datatypes import MtiDeviceInfo
from .xbus_reader import XbusStreamReader


type XbusMessageCallback = Callable[[XbusMessage], None]
type ErrorCallback = Callable[[Exception], None]


class MtiDeviceCommunicator:
    """
    Owns the serial port and XbusStreamReader for a single connected MTi device.

    Opens the port on construction and immediately puts the device in config state.
    Fires registered callbacks when messages arrive or the reader thread faults.
    """

    def __init__(
        self,
        port_info: MtiPortInfo,
        device_info: MtiDeviceInfo,
        timeout: float = 5.0,
    ) -> None:
        """
        Open the serial port and put the device in config state.

        Arguments
        ---------
        port_info: Connection parameters for the serial port to open.
        device_info: Identity information for the device on this port.
        timeout: Default timeout in seconds for Xbus send-and-receive calls.
        """
        self._port_info: MtiPortInfo = port_info
        self._device_info: MtiDeviceInfo = device_info
        self._timeout: float = timeout
        self._message_callback: XbusMessageCallback | None = None
        self._error_callback: ErrorCallback | None = None
        self._ser: serial.Serial = open_serial_port(
            port_info.port,
            port_info.baud,
            read_timeout=0.1,
        )
        self._ser.reset_input_buffer()
        self._reader: XbusStreamReader = XbusStreamReader(
            ser=self._ser,
            on_message=self._dispatch_message,
            on_error=self._dispatch_error,
        )
        try:
            self.goto_config()
        except Exception:
            self._ser.close()
            raise

    @property
    def port(self) -> str:
        """Serial port path (e.g. '/dev/ttyUSB0')."""
        return str(self._ser.port)

    def port_info(self) -> MtiPortInfo:
        """Return the connection parameters for this port."""
        return self._port_info

    def device_info(self) -> MtiDeviceInfo:
        """Return the identity information for the connected device."""
        return self._device_info

    # --- Callback registration ---

    def set_message_callback(self, callback: XbusMessageCallback) -> None:
        """
        Register a callback invoked for each received XbusMessage.

        Arguments
        ---------
        callback: Called from the XbusStreamReader thread with each message.
        """
        self._message_callback = callback

    def set_error_callback(self, callback: ErrorCallback) -> None:
        """
        Register a callback invoked when the reader thread faults.

        Arguments
        ---------
        callback: Called from the XbusStreamReader thread with the raised exception.
        """
        self._error_callback = callback

    # --- Communication ---

    def send(self, message: XbusMessage) -> None:
        """
        Send an Xbus message without waiting for a response.

        Arguments
        ---------
        message: The Xbus message to write to the serial port.
        """
        send_message(self._ser, message)

    def send_and_receive(
        self,
        message: XbusMessage,
        expected_mid: XbusMessageID,
        timeout: float | None = None,
    ) -> XbusMessage:
        """
        Send an Xbus message and wait for its acknowledgement.

        Arguments
        ---------
        message: The Xbus message to send.
        expected_mid: Message ID of the expected response.
        timeout: Maximum seconds to wait for a response. Defaults to the communicator timeout.

        Returns
        -------
        The first matching XbusMessage received before the deadline.
        """
        effective_timeout: float = timeout if timeout is not None else self._timeout
        return serial_send_and_receive(
            self._ser,
            message,
            expected_mid=expected_mid,
            timeout=effective_timeout,
        )

    # --- State transitions ---

    def goto_config(self) -> None:
        """Stop the stream reader and put the device in config state."""
        self._reader.stop()
        self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOCONFIG),
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
        )

    def goto_measurement(self) -> None:
        """Put the device in measurement state and start the stream reader."""
        self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOMEASUREMENT),
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
        )
        self._reader.start()

    # --- Port management ---

    def flush(self) -> None:
        """Reset the serial input buffer."""
        self._ser.reset_input_buffer()

    def close(self) -> None:
        """Stop the stream reader and close the serial port."""
        self._reader.stop()
        self._ser.close()

    # --- Internal ---

    def _dispatch_message(self, message: XbusMessage) -> None:
        if self._message_callback is not None:
            self._message_callback(message)

    def _dispatch_error(self, exc: Exception) -> None:
        if self._error_callback is not None:
            self._error_callback(exc)
