"""
MtiDevice — handle to a single connected XSens MTi sensor.
"""

from __future__ import annotations

import threading

from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from typing import get_args
from loguru import logger
from xsensmti.mtdata2 import (
    Measurement,
    decode_all_measurements,
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
    MtiDeviceInfo,
    MtiDeviceOptions,
    MtiDeviceOutputConfig,
    MtiDeviceState,
    MtiMessage,
    MtiMessageHeader,
    MtiPortInfo,
    Sample,
)


type MtiMessageCallback = Callable[[MtiMessage], None]
type MtiSampleCallback[T: Measurement] = Callable[[Sample[T]], None]

type MeasurementType = type[Measurement]
type MtiSampleCallbackRegistry = dict[MeasurementType, MtiSampleCallback[Measurement]]


class MtiDevice:
    def __init__(
        self,
        communicator: MtiDeviceCommunicator,
        timeout: float = 5.0,
        buffer_size: int = 100,
    ) -> None:
        self._communicator: MtiDeviceCommunicator = communicator
        self._timeout: float = timeout
        self._state_lock: threading.Lock = threading.Lock()
        self._state_value: MtiDeviceState = MtiDeviceState.CONFIG
        self._on_message_callback: MtiMessageCallback | None = None
        self._measurement_callbacks: MtiSampleCallbackRegistry = dict()
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

    def device_info(self) -> MtiDeviceInfo:
        return self._communicator.device_info()

    def port_info(self) -> MtiPortInfo:
        return self._communicator.port_info()

    # --- State ---

    def device_state(self) -> MtiDeviceState:
        return self._state

    def is_measuring(self) -> bool:
        return self._state == MtiDeviceState.MEASUREMENT

    def set_on_message(self, callback: MtiMessageCallback | None) -> None:
        with self._callback_lock:
            self._on_message_callback = callback

    def set_on_sample[T: Measurement](
        self,
        sample_type: type[Sample[T]],
        callback: MtiSampleCallback[T] | None,
    ) -> None:
        """
        Register a callback invoked for a specific Sample type.

        You subscribe by Sample type (e.g. OrientationQuaternionSample) and the
        callback receives exactly that Sample — i.e. the registration type and
        the received type are the same.

        Arguments
        ---------
        sample_type: The Sample alias to match (e.g. OrientationQuaternionSample).
        callback: Callable receiving the Sample, or None to clear the registration.
        """
        measurement_type: type[Measurement] = get_args(sample_type)[0]
        with self._callback_lock:
            if callback is None:
                self._measurement_callbacks.pop(measurement_type, None)
            else:
                self._measurement_callbacks[measurement_type] = callback  # type: ignore[assignment]

    def update(self) -> None:
        with self._buffer_lock:
            messages: list[MtiMessage] = list(self._buffer)
            self._buffer.clear()
        with self._callback_lock:
            message_callback: MtiMessageCallback | None = self._on_message_callback
            measurement_callbacks: MtiSampleCallbackRegistry = dict(
                self._measurement_callbacks
            )
        for message in messages:
            if message_callback is not None:
                message_callback(message)
            self._handle_measurements(message, measurement_callbacks)

    def _handle_measurements(
        self,
        message: MtiMessage,
        measurement_callbacks: MtiSampleCallbackRegistry,
    ) -> None:
        if (
            not measurement_callbacks
            or message.xbus_message.mid != XbusMessageID.MTDATA2
        ):
            return
        for measurement in decode_all_measurements(message.xbus_message):
            measurement_callback: MtiSampleCallback[Measurement] | None = (
                measurement_callbacks.get(type(measurement))
            )
            if measurement_callback is None:
                continue
            measurement_callback(Sample(header=message.header, payload=measurement))

    def close(self) -> None:
        self._communicator.close()

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
        self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION, config.to_payload()),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )

    def request_output_config(self) -> MtiDeviceOutputConfig:
        message: XbusMessage = self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOutputConfig.from_payload(message.payload)

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
                device_info=self._communicator.device_info(),
                timestamp=datetime.now(tz=timezone.utc),
            ),
            xbus_message=xbus_message,
        )
        with self._buffer_lock:
            self._buffer.append(message)

    def _on_reader_error(self, exc: Exception) -> None:
        self._state = MtiDeviceState.CONFIG
