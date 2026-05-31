"""
MtiDevice — handle to a single connected XSens MTi sensor.
"""

from __future__ import annotations

import threading

from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from loguru import logger
from xsensmti.mtdata2 import (
    MtData2PacketID,
    Reading,
    decode_all_readings,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .communicator import MtiDeviceCommunicator
from .datatypes import (
    MtiDeviceConfig,
    MtiDeviceFilterProfile,
    MtiDeviceID,
    MtiDeviceOptions,
    MtiDeviceOutputConfig,
    MtiDeviceState,
    MtiMessage,
    MtiMessageHeader,
)


type MessageCallback = Callable[[MtiMessage], None]
type ReadingType = type[Reading]
type ReadingCallback[T: Reading] = Callable[[MtiMessageHeader, T], None]
type ReadingCallbackRegistry = dict[ReadingType, ReadingCallback[Reading]]


class MtiDevice:
    def __init__(
        self,
        device_id: MtiDeviceID,
        communicator: MtiDeviceCommunicator,
        timeout: float = 5.0,
        buffer_size: int = 100,
    ) -> None:
        self._device_id: MtiDeviceID = device_id
        self._communicator: MtiDeviceCommunicator = communicator
        self._timeout: float = timeout
        self._state_lock: threading.Lock = threading.Lock()
        self._state_value: MtiDeviceState = MtiDeviceState.CONFIG
        self._on_message_callback: MessageCallback | None = None
        self._reading_callbacks: ReadingCallbackRegistry = dict()
        self._callback_lock: threading.Lock = threading.Lock()
        self._buffer: deque[MtiMessage] = deque(maxlen=buffer_size)
        self._buffer_lock: threading.Lock = threading.Lock()
        self._communicator.set_message_callback(self._on_message)
        self._communicator.set_error_callback(self._on_reader_error)

    @property
    def _state(self) -> MtiDeviceState:
        with self._state_lock:
            return self._state_value

    @_state.setter
    def _state(self, value: MtiDeviceState) -> None:
        with self._state_lock:
            self._state_value = value

    # --- Identity ---

    def device_id(self) -> MtiDeviceID:
        return self._device_id

    # --- State ---

    def device_state(self) -> MtiDeviceState:
        return self._state

    def is_measuring(self) -> bool:
        return self._state == MtiDeviceState.MEASUREMENT

    def set_on_message(self, callback: MessageCallback | None) -> None:
        with self._callback_lock:
            self._on_message_callback = callback

    def set_on_reading[T: Reading](
        self,
        reading_type: type[T],
        callback: ReadingCallback[T] | None,
    ) -> None:
        with self._callback_lock:
            if callback is None:
                self._reading_callbacks.pop(reading_type, None)  # type: ignore[arg-type]
            else:
                self._reading_callbacks[reading_type] = callback  # type: ignore[index, assignment]

    def update(self) -> None:
        with self._buffer_lock:
            messages: list[MtiMessage] = list(self._buffer)
            self._buffer.clear()
        with self._callback_lock:
            message_callback: MessageCallback | None = self._on_message_callback
            reading_callbacks: ReadingCallbackRegistry = dict(self._reading_callbacks)
        for message in messages:
            if message_callback is not None:
                message_callback(message)
            self._handle_readings(message, reading_callbacks)

    def _handle_readings(
        self,
        message: MtiMessage,
        reading_callbacks: ReadingCallbackRegistry,
    ) -> None:
        if not reading_callbacks or message.xbus_message.mid != XbusMessageID.MTDATA2:
            return
        for reading in decode_all_readings(message.xbus_message):
            reading_type: type = type(reading)
            if reading_type not in reading_callbacks:
                continue
            reading_callback: ReadingCallback[Reading] = reading_callbacks[reading_type]
            reading_callback(message.header, reading)

    def goto_config(self) -> None:
        self._communicator.goto_config()
        self._state = MtiDeviceState.CONFIG
        logger.debug(f"{self._communicator.port}: entered config mode")

    def goto_measurement(self) -> None:
        self._communicator.goto_measurement()
        self._state = MtiDeviceState.MEASUREMENT
        logger.debug(f"{self._communicator.port}: entered measurement mode")

    def reset(self) -> None:
        if self.is_measuring():
            self._communicator.goto_config()
        self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.RESET),
            expected_mid=XbusMessageID.RESET_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG

    def restore_factory_defaults(self) -> None:
        if self.is_measuring():
            self._communicator.goto_config()
        self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.RESTORE_FACTORY_DEFAULTS),
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
        self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION, payload),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )

    def output_config(self) -> MtiDeviceOutputConfig:
        message: XbusMessage = self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )
        result: MtiDeviceOutputConfig = []
        for i in range(0, len(message.payload), 4):
            odi: MtData2PacketID = MtData2PacketID(
                int.from_bytes(message.payload[i : i + 2], "big")
            )
            rate: int = int.from_bytes(message.payload[i + 2 : i + 4], "big")
            result.append((odi, rate))
        return result

    def request_options(self) -> MtiDeviceOptions:
        message: XbusMessage = self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OPTION_FLAGS),
            expected_mid=XbusMessageID.OPTION_FLAGS_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOptions.from_payload(message.payload)

    def request_filter_profile(self) -> MtiDeviceFilterProfile:
        message: XbusMessage = self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.FILTER_PROFILE),
            expected_mid=XbusMessageID.FILTER_PROFILE_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceFilterProfile.from_payload(message.payload)

    def request_config(self) -> MtiDeviceConfig:
        message: XbusMessage = self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_CONFIGURATION),
            expected_mid=XbusMessageID.CONFIGURATION,
            timeout=self._timeout,
        )
        return MtiDeviceConfig.from_payload(message.payload)

    # --- Raw comms ---

    def send_custom_message(
        self,
        message: XbusMessage,
        expected_mid: XbusMessageID,
        timeout: float | None = None,
    ) -> XbusMessage:
        return self._communicator.send_and_receive(
            message,
            expected_mid=expected_mid,
            timeout=timeout,
        )

    # --- Internal ---

    def _on_message(self, xbus_message: XbusMessage) -> None:
        message = MtiMessage(
            header=MtiMessageHeader(
                device_id=self._device_id,
                timestamp=datetime.now(tz=timezone.utc),
            ),
            xbus_message=xbus_message,
        )
        with self._buffer_lock:
            self._buffer.append(message)

    def _on_reader_error(self, exc: Exception) -> None:
        self._state = MtiDeviceState.CONFIG
