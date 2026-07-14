"""
AsyncMtiDevice — async handle to a single connected XSens MTi sensor.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any, get_args
from loguru import logger
from xsensmti.mtdata2 import (
    Measurement,
    decode_all_measurements,
)
from xsensmti.xbus import (
    XbusBaudCode,
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
    resolve_filter_profile,
    uses_modern_filter_profile,
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

        Args:
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

        Args:
            callback: Async callable receiving the full MtiMessage, or None to clear.
        """
        self._on_message_callback = callback

    def set_on_sample[T: Measurement](
        self,
        sample_type: type[Sample[T]],
        callback: AsyncMtiSampleCallback[T] | None,
    ) -> None:
        """
        Register an async callback invoked for a specific Sample type.

        You subscribe by Sample type (e.g. OrientationQuaternionSample) and the
        callback receives exactly that Sample — i.e. the registration type and
        the received type are the same.

        Args:
            sample_type: The Sample alias to match (e.g. OrientationQuaternionSample).
            callback: Async callable receiving the Sample, or None to clear the registration.
        """
        measurement_type: type[Measurement] = get_args(sample_type)[0]
        if callback is None:
            self._measurement_callbacks.pop(measurement_type, None)
        else:
            self._measurement_callbacks[measurement_type] = callback  # type: ignore[assignment]

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

        Args:
            config: The MTData2 output configuration to apply.
        """
        await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION, config.to_payload()),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )

    async def request_output_config(self) -> MtiDeviceOutputConfig:
        """
        Request and return the current MTData2 output configuration.

        Returns:
            The MTData2 output configuration currently set on the device.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OUTPUT_CONFIGURATION),
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOutputConfig.from_payload(message.payload)

    async def request_baudrate(self) -> int:
        """
        Request the baud rate the device is configured to use, in bps.

        Only answerable once communication is established — the request is itself
        an Xbus message. Use discover_baudrate() when the rate is unknown.

        Returns:
            The configured baud rate in bps.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.SET_BAUDRATE),
            expected_mid=XbusMessageID.SET_BAUDRATE_ACK,
            timeout=self._timeout,
        )
        return XbusBaudCode(message.payload[0]).to_rate()

    async def request_options(self) -> MtiDeviceOptions:
        """
        Request and return the current device option flags.

        Returns:
            The current MtiDeviceOptions.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OPTION_FLAGS),
            expected_mid=XbusMessageID.OPTION_FLAGS_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceOptions.from_payload(message.payload)

    async def set_options(self, options: MtiDeviceOptions) -> None:
        """
        Set the device option flags.

        Args:
            options: The option flags to apply. Every flag is written explicitly.
        """
        await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.OPTION_FLAGS, options.to_payload()),
            expected_mid=XbusMessageID.OPTION_FLAGS_ACK,
            timeout=self._timeout,
        )

    async def request_filter_profile(self) -> MtiDeviceFilterProfile:
        """
        Request and return the current filter profile.

        The FILTER_PROFILE_ACK payload is incomplete — classic devices report only
        the numeric profile type, modern devices only the label — so the profile is
        resolved against the device's available profiles to recover the full triple.
        This costs a second round trip.

        Returns:
            The current MtiDeviceFilterProfile.
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.FILTER_PROFILE),
            expected_mid=XbusMessageID.FILTER_PROFILE_ACK,
            timeout=self._timeout,
        )
        profile: MtiDeviceFilterProfile = MtiDeviceFilterProfile.from_payload(
            message.payload
        )
        available: list[
            MtiDeviceFilterProfile
        ] = await self.request_available_filter_profiles()
        return resolve_filter_profile(profile, available)

    async def set_filter_profile(self, profile: MtiDeviceFilterProfile) -> None:
        """
        Select one of the device's predefined filter profiles.

        Pass a profile obtained from request_filter_profile() or
        request_available_filter_profiles(). The profile is not validated here —
        the device rejects an unknown one with an MtiDeviceError.

        Args:
            profile: The filter profile to select.
        """
        await self._communicator.send_and_receive(
            build_xbus_command(
                XbusMessageID.FILTER_PROFILE, self._encode_filter_profile(profile)
            ),
            expected_mid=XbusMessageID.FILTER_PROFILE_ACK,
            timeout=self._timeout,
        )

    async def request_available_filter_profiles(self) -> list[MtiDeviceFilterProfile]:
        """
        Request the filter profiles predefined in the device's firmware.

        Returns:
            The profiles the device supports, which are the valid arguments to
            set_filter_profile().
        """
        message: XbusMessage = await self._communicator.send_and_receive(
            build_xbus_command(XbusMessageID.AVAILABLE_FILTER_PROFILES),
            expected_mid=XbusMessageID.AVAILABLE_FILTER_PROFILES_ACK,
            timeout=self._timeout,
        )
        return MtiDeviceFilterProfile.list_from_payload(message.payload)

    def _encode_filter_profile(self, profile: MtiDeviceFilterProfile) -> bytes:
        product_code: str = self._communicator.device_info().product_code
        if uses_modern_filter_profile(product_code):
            return profile.to_modern_payload()
        return profile.to_classic_payload()

    async def request_config(self) -> MtiDeviceConfig:
        """
        Request and return the full device configuration.

        Returns:
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

        Args:
            message: The Xbus message to send.
            expected_mid: Message ID of the expected response.
            timeout: Maximum seconds to wait. Defaults to the device timeout.

        Returns:
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
                device_info=self._communicator.device_info(),
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
