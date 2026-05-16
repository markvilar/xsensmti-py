"""
MtiDevice — handle to a single connected XSens MTi sensor.
"""

from __future__ import annotations

import threading
import serial

from collections import deque
from loguru import logger
from xsensmti.port import MtiPortInfo
from xsensmti.serial import send_and_receive
from xsensmti.mtdata2 import OutputDataIdentifier
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
)
from .datatypes import (
    MtiDeviceConfig,
    MtiDeviceFilterProfile,
    MtiDeviceOptions,
    MtiDeviceOutputConfig,
    MtiDeviceState,
)
from .xbus_reader import XbusStreamReader


class MtiDevice:
    def __init__(
        self,
        port_info: MtiPortInfo,
        firmware_version: str,
        hardware_version: str,
        ser: serial.Serial,
        timeout: float = 5.0,
        buffer_size: int = 100,
    ) -> None:
        self._port_info: MtiPortInfo = port_info
        self._firmware_version: str = firmware_version
        self._hardware_version: str = hardware_version
        self._ser: serial.Serial = ser
        self._timeout: float = timeout
        self._state: MtiDeviceState = MtiDeviceState.CONFIG
        self._buffer: deque[XbusMessage] = deque(maxlen=buffer_size)
        self._buffer_lock: threading.Lock = threading.Lock()
        self._reader: XbusStreamReader = XbusStreamReader(
            ser=self._ser,
            on_message=self._on_message,
            on_error=self._on_reader_error,
        )

    # --- Identity ---

    def device_id(self) -> int:
        return self._port_info.device_id

    def product_code(self) -> str:
        return self._port_info.product_code

    def port_name(self) -> str:
        return self._port_info.port

    def baud_rate(self) -> int:
        return self._port_info.baud

    def port_info(self) -> MtiPortInfo:
        return self._port_info

    def firmware_version(self) -> str:
        return self._firmware_version

    def hardware_version(self) -> str:
        return self._hardware_version

    # --- State ---

    def device_state(self) -> MtiDeviceState:
        return self._state

    def is_measuring(self) -> bool:
        return self._state == MtiDeviceState.MEASUREMENT

    def goto_config(self) -> None:
        self._reader.stop()
        send_and_receive(
            self._ser,
            XbusMessageID.GOTOCONFIG,
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG
        logger.debug(f"{self._port_info.port}: entered config mode")

    def goto_measurement(self) -> None:
        send_and_receive(
            self._ser,
            XbusMessageID.GOTOMEASUREMENT,
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.MEASUREMENT
        self._reader.start()
        logger.debug(f"{self._port_info.port}: entered measurement mode")

    def reset(self) -> None:
        self._reader.stop()
        send_and_receive(
            self._ser,
            XbusMessageID.RESET,
            expected_mid=XbusMessageID.RESET_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG

    def restore_factory_defaults(self) -> None:
        self._reader.stop()
        send_and_receive(
            self._ser,
            XbusMessageID.RESTORE_FACTORY_DEFAULTS,
            expected_mid=XbusMessageID.RESTORE_FACTORY_DEFAULTS_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG

    # --- Output configuration ---

    def set_output_config(self, config: MtiDeviceOutputConfig) -> None:
        payload: bytes = b"".join(
            int(odi).to_bytes(2, "big") + rate.to_bytes(2, "big")
            for odi, rate in config
        )
        send_and_receive(
            self._ser,
            XbusMessageID.OUTPUT_CONFIGURATION,
            payload=payload,
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )

    def output_config(self) -> MtiDeviceOutputConfig:
        msg: XbusMessage = send_and_receive(
            self._ser,
            XbusMessageID.OUTPUT_CONFIGURATION,
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )
        result: MtiDeviceOutputConfig = []
        for i in range(0, len(msg.payload), 4):
            odi: OutputDataIdentifier = OutputDataIdentifier(
                int.from_bytes(msg.payload[i : i + 2], "big")
            )
            rate: int = int.from_bytes(msg.payload[i + 2 : i + 4], "big")
            result.append((odi, rate))
        return result

    def request_options(self) -> MtiDeviceOptions:
        msg: XbusMessage = send_and_receive(
            self._ser,
            XbusMessageID.OPTION_FLAGS,
            expected_mid=XbusMessageID.OPTION_FLAGS_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOptions.from_payload(msg.payload)

    def request_filter_profile(self) -> MtiDeviceFilterProfile:
        msg: XbusMessage = send_and_receive(
            self._ser,
            XbusMessageID.FILTER_PROFILE,
            expected_mid=XbusMessageID.FILTER_PROFILE_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceFilterProfile.from_payload(msg.payload)

    def request_config(self) -> MtiDeviceConfig:
        msg: XbusMessage = send_and_receive(
            self._ser,
            XbusMessageID.REQ_CONFIGURATION,
            expected_mid=XbusMessageID.CONFIGURATION,
            timeout=self._timeout,
        )
        return MtiDeviceConfig.from_payload(msg.payload)

    # --- Data retrieval ---

    def take_first_data_packet_in_queue(self) -> XbusMessage | None:
        try:
            return self._buffer.popleft()
        except IndexError:
            return None

    def last_available_live_data(self) -> XbusMessage | None:
        with self._buffer_lock:
            if not self._buffer:
                return None
            message: XbusMessage = self._buffer[-1]
            self._buffer.clear()
            return message

    def request_data(self) -> XbusMessage:
        return send_and_receive(
            self._ser,
            XbusMessageID.REQ_DATA,
            expected_mid=XbusMessageID.MTDATA2,
            timeout=self._timeout,
        )

    # --- Raw comms ---

    def send_custom_message(
        self,
        mid: XbusMessageID,
        payload: bytes = b"",
        expected_mid: XbusMessageID | None = None,
        timeout: float = 2.0,
    ) -> XbusMessage:
        return send_and_receive(
            self._ser,
            mid,
            payload=payload,
            expected_mid=expected_mid,
            timeout=timeout,
        )

    def send_raw_message(self, data: bytes) -> None:
        self._ser.write(data)

    def close(self) -> None:
        if self.is_measuring():
            self.goto_config()
        self._ser.close()

    def reopen_port(self) -> None:
        self._reader.stop()
        self._ser.close()
        self._ser.open()
        self._state = MtiDeviceState.CONFIG

    # --- Internal ---

    def _on_message(self, message: XbusMessage) -> None:
        if message.header.mid == XbusMessageID.MTDATA2:
            with self._buffer_lock:
                self._buffer.append(message)

    def _on_reader_error(self, exc: Exception) -> None:
        self._state = MtiDeviceState.CONFIG
