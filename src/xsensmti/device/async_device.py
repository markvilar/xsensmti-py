"""
AsyncMtiDevice — async handle to a single connected XSens MTi sensor.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any
from loguru import logger
from xsensmti.mtdata2 import (
    Measurement,
    MtData2PacketID,
    decode_all_measurements,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .async_communicator import AsyncMtiDeviceCommunicator
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


type AsyncMtiMessageCallback = Callable[[MtiMessage], Coroutine[Any, Any, None]]
type AsyncMtiSampleCallback[T: Measurement] = Callable[
    [Sample[T]], Coroutine[Any, Any, None]
]

type MeasurementType = type[Measurement]
type AsyncMtiSampleCallbackRegistry = dict[
    MeasurementType, AsyncMtiSampleCallback[Measurement]
]


class AsyncMtiDevice:
    """
    Async handle to a single connected XSens MTi sensor.

    Wraps an AsyncMtiDeviceCommunicator and fires async callbacks when messages
    arrive. The communicator's internal dispatch task calls _on_message directly,
    so no buffer or update() call is needed.
    """

    def __init__(
        self,
        communicator: AsyncMtiDeviceCommunicator,
        timeout: float = 5.0,
    ) -> None:
        """
        Wrap a communicator and register internal async callbacks on it.

        Arguments
        ---------
        communicator: Open communicator for the device, already in config state.
        timeout: Default timeout in seconds for Xbus send-and-receive calls.
        """
        self._communicator: AsyncMtiDeviceCommunicator = communicator
        self._timeout: float = timeout
        self._state: MtiDeviceState = MtiDeviceState.CONFIG
        self._on_message_callback: AsyncMtiMessageCallback | None = None
        self._measurement_callbacks: AsyncMtiSampleCallbackRegistry = dict()
        self._communicator.set_message_callback(self._on_message)
        self._communicator.set_error_callback(self._on_reader_error)

    # --- Identity ---

    def device_info(self) -> MtiDeviceInfo:
        """Return the identity information for the connected device."""
        return self._communicator.device_info()

    def port_info(self) -> MtiPortInfo:
        """Return the connection parameters for this device's port."""
        return self._communicator.port_info()

    # --- State ---

    def device_state(self) -> MtiDeviceState:
        """Return the current device state (config or measurement)."""
        return self._state

    def is_measuring(self) -> bool:
        """Return True if the device is in measurement state."""
        return self._state == MtiDeviceState.MEASUREMENT

    # --- Callback registration ---

    def set_on_message(self, callback: AsyncMtiMessageCallback | None) -> None:
        """
        Register an async callback invoked for each received MtiMessage.

        Arguments
        ---------
        callback: Async callable receiving the full MtiMessage, or None to clear.
        """
        self._on_message_callback = callback

    def set_on_measurement[T: Measurement](
        self,
        measurement_type: type[T],
        callback: AsyncMtiSampleCallback[T] | None,
    ) -> None:
        """
        Register an async callback invoked for a specific measurement type.

        You subscribe by measurement type (e.g. OrientationQuaternion) and the
        callback receives that measurement wrapped in a Sample together with its
        receipt metadata — i.e. Sample[T], not a bare T.

        Arguments
        ---------
        measurement_type: The Measurement subclass to match (e.g. OrientationQuaternion).
        callback: Async callable receiving the Sample, or None to clear the registration.
        """
        if callback is None:
            self._measurement_callbacks.pop(measurement_type, None)  # type: ignore[arg-type]
        else:
            self._measurement_callbacks[measurement_type] = callback  # type: ignore[index, assignment]

    # --- State transitions ---

    async def goto_config(self) -> None:
        """Put the device in config state."""
        await self._communicator.goto_config()
        self._state = MtiDeviceState.CONFIG
        logger.debug(f"{self._communicator.port}: entered config mode")

    async def goto_measurement(self) -> None:
        """Put the device in measurement state."""
        await self._communicator.goto_measurement()
        self._state = MtiDeviceState.MEASUREMENT
        logger.debug(f"{self._communicator.port}: entered measurement mode")

    async def close(self) -> None:
        """Close the communicator and release the serial port."""
        await self._communicator.close()

    # --- Commands ---

    async def reset(self) -> None:
        """Reset the device and return it to config state."""
        if self.is_measuring():
            await self._communicator.goto_config()
        await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.RESET),
            expected_mid=XbusMessageID.RESET_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG

    async def restore_factory_defaults(self) -> None:
        """Restore factory defaults and return the device to config state."""
        if self.is_measuring():
            await self._communicator.goto_config()
        await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.RESTORE_FACTORY_DEFAULTS),
            expected_mid=XbusMessageID.RESTORE_FACTORY_DEFAULTS_ACK,
            timeout=self._timeout,
        )
        self._state = MtiDeviceState.CONFIG

    # --- Output configuration ---

    async def set_output_config(self, config: MtiDeviceOutputConfig) -> None:
        """
        Set the MTData2 output configuration.

        Arguments
        ---------
        config: List of (OutputDataIdentifier, rate) pairs to configure.
        """
        payload: bytes = b"".join(
            int(odi).to_bytes(2, "big") + rate.to_bytes(2, "big")
            for odi, rate in config
        )
        await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION, payload),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )

    async def output_config(self) -> MtiDeviceOutputConfig:
        """
        Request and return the current MTData2 output configuration.

        Returns
        -------
        List of (OutputDataIdentifier, rate) pairs currently configured.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
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

    async def request_options(self) -> MtiDeviceOptions:
        """
        Request and return the current device option flags.

        Returns
        -------
        The current MtiDeviceOptions.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OPTION_FLAGS),
            expected_mid=XbusMessageID.OPTION_FLAGS_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOptions.from_payload(message.payload)

    async def request_filter_profile(self) -> MtiDeviceFilterProfile:
        """
        Request and return the current filter profile.

        Returns
        -------
        The current MtiDeviceFilterProfile.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.FILTER_PROFILE),
            expected_mid=XbusMessageID.FILTER_PROFILE_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceFilterProfile.from_payload(message.payload)

    async def request_config(self) -> MtiDeviceConfig:
        """
        Request and return the full device configuration.

        Returns
        -------
        The current MtiDeviceConfig.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.REQ_CONFIGURATION),
            expected_mid=XbusMessageID.CONFIGURATION,
            timeout=self._timeout,
        )
        return MtiDeviceConfig.from_payload(message.payload)

    # --- Raw comms ---

    async def send_custom_message(
        self,
        message: XbusMessage,
        expected_mid: XbusMessageID,
        timeout: float | None = None,
    ) -> XbusMessage:
        """
        Send a raw Xbus message and wait for its acknowledgement.

        Arguments
        ---------
        message: The Xbus message to send.
        expected_mid: Message ID of the expected response.
        timeout: Maximum seconds to wait. Defaults to the device timeout.

        Returns
        -------
        The first matching XbusMessage received before the deadline.
        """
        return await self._communicator.send_and_receive(
            message,
            expected_mid=expected_mid,
            timeout=timeout,
        )

    # --- Internal ---

    async def _on_message(self, xbus_message: XbusMessage) -> None:
        message: MtiMessage = MtiMessage(
            header=MtiMessageHeader(
                device_id=self._communicator.device_info(),
                timestamp=datetime.now(tz=timezone.utc),
            ),
            xbus_message=xbus_message,
        )
        if self._on_message_callback is not None:
            await self._on_message_callback(message)
        await self._handle_measurements(message)

    async def _handle_measurements(self, message: MtiMessage) -> None:
        if not self._measurement_callbacks:
            return
        if message.xbus_message.mid != XbusMessageID.MTDATA2:
            return
        for measurement in decode_all_measurements(message.xbus_message):
            measurement_callback: AsyncMtiSampleCallback[Measurement] | None = (
                self._measurement_callbacks.get(type(measurement))
            )
            if measurement_callback is None:
                continue
            await measurement_callback(
                Sample(header=message.header, payload=measurement)
            )

    async def _on_reader_error(self, exc: Exception) -> None:
        logger.error(f"{self._communicator.port}: reader error: {exc}")
        self._state = MtiDeviceState.CONFIG
