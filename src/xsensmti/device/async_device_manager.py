"""
AsyncMtiDeviceManager — async discovery and lifecycle management for multiple MTi devices.
"""

from __future__ import annotations

import asyncio

from collections.abc import Callable, Coroutine
from typing import Any
from loguru import logger
from xsensmti.device.datatypes import (
    MtiDeviceID,
    MtiDeviceInfo,
    MtiPortInfo,
    MtiProbeResult,
    MtiScanResult,
)

from .async_communicator import AsyncMtiDeviceCommunicator
from .async_device import AsyncMtiDevice
from .manager import MtiDeviceManagerConfig
from .scanner import probe_port, scan_ports


type AsyncConnectCallback = Callable[[AsyncMtiDevice], Coroutine[Any, Any, None]]
type AsyncDisconnectCallback = Callable[[MtiDeviceInfo], Coroutine[Any, Any, None]]


class AsyncMtiDeviceManager:
    """
    Discovers and manages the lifecycle of multiple connected MTi devices.

    Runs two asyncio Tasks: a scan loop that detects port appearances and
    disappearances, and a probe loop that attempts to open unprobed ports as MTi
    devices. Fires async callbacks when devices connect or disconnect. Ports that
    fail probing are retried on each probe cycle.
    """

    def __init__(
        self,
        on_connect: AsyncConnectCallback,
        on_disconnect: AsyncDisconnectCallback | None = None,
        config: MtiDeviceManagerConfig = MtiDeviceManagerConfig(),
    ) -> None:
        """
        Initialise the manager. Call `start()` or use as an async context manager to begin scanning.

        Arguments
        ---------
        on_connect: Async callback invoked when a new device is opened.
        on_disconnect: Async callback invoked when an active device disappears.
        config: Tuning parameters for scanning and probing intervals.
        """
        self._on_connect: AsyncConnectCallback = on_connect
        self._on_disconnect: AsyncDisconnectCallback | None = on_disconnect
        self._config: MtiDeviceManagerConfig = config

        self._lock: asyncio.Lock = asyncio.Lock()
        self._unprobed_ports: set[MtiPortInfo] = set()
        self._devices: dict[MtiDeviceID, AsyncMtiDevice] = dict()

        self._scan_task: asyncio.Task[None] | None = None
        self._probe_task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event = asyncio.Event()

    # --- Public API ---

    async def start(self) -> None:
        """Start the background scan and probe tasks."""
        self._stop_event.clear()
        self._scan_task = asyncio.create_task(self._scan_loop(), name="mti-scan")
        self._probe_task = asyncio.create_task(self._probe_loop(), name="mti-probe")

    async def stop(self) -> None:
        """Stop both tasks and close all open devices."""
        self._stop_event.set()
        for task in (self._scan_task, self._probe_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._scan_task = None
        self._probe_task = None

        async with self._lock:
            devices: list[AsyncMtiDevice] = list(self._devices.values())
            self._devices.clear()
            self._unprobed_ports.clear()

        for device in devices:
            try:
                await device.close()
            except Exception as exc:
                logger.debug(f"error closing device on stop: {exc}")

    def active_devices(self) -> list[AsyncMtiDevice]:
        """Return a snapshot of currently active devices."""
        return list(self._devices.values())

    def active_device_ids(self) -> list[MtiDeviceID]:
        """Return a snapshot of currently active device IDs."""
        return list(self._devices.keys())

    def get_active_device_info(self, device_id: MtiDeviceID) -> MtiDeviceInfo | None:
        """
        Return the device info for an active device, or None if not found.

        Arguments
        ---------
        device_id: Device ID to look up.

        Returns
        -------
        The MtiDeviceInfo for the device, or None.
        """
        device: AsyncMtiDevice | None = self._devices.get(device_id)
        return device.device_info() if device is not None else None

    def get_active_port_info(self, device_id: MtiDeviceID) -> MtiPortInfo | None:
        """
        Return the port info for an active device, or None if not found.

        Arguments
        ---------
        device_id: Device ID to look up.

        Returns
        -------
        The MtiPortInfo for the device, or None.
        """
        device: AsyncMtiDevice | None = self._devices.get(device_id)
        return device.port_info() if device is not None else None

    async def __aenter__(self) -> AsyncMtiDeviceManager:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    # --- Scan ---

    async def _scan_loop(self) -> None:
        while not self._stop_event.is_set():
            await self._run_scan_cycle()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._config.scan_interval,
                )
                break
            except asyncio.TimeoutError:
                pass

    async def _run_scan_cycle(self) -> None:
        scan_results: list[MtiScanResult] = await asyncio.to_thread(
            scan_ports, baud=self._config.baud
        )
        current_port_infos: set[MtiPortInfo] = {r.port_info for r in scan_results}
        current_ports: set[str] = {pi.port for pi in current_port_infos}

        async with self._lock:
            unprobed_port_paths: set[str] = {pi.port for pi in self._unprobed_ports}
            active_port_paths: set[str] = {
                device.port_info().port for device in self._devices.values()
            }

        known_ports: set[str] = unprobed_port_paths | active_port_paths
        disappeared_ports: set[str] = known_ports - current_ports
        appeared_port_infos: set[MtiPortInfo] = {
            pi for pi in current_port_infos if pi.port not in known_ports
        }

        for port in disappeared_ports:
            await self._handle_disappeared_port(port)

        async with self._lock:
            self._unprobed_ports.update(appeared_port_infos)

    async def _handle_disappeared_port(self, port: str) -> None:
        async with self._lock:
            self._unprobed_ports = {
                pi for pi in self._unprobed_ports if pi.port != port
            }
            device_id: MtiDeviceID | None = next(
                (
                    did
                    for did, device in self._devices.items()
                    if device.port_info().port == port
                ),
                None,
            )
            device: AsyncMtiDevice | None = (
                self._devices.pop(device_id, None) if device_id is not None else None
            )

        if device is not None:
            await self._handle_disconnected_device(device, port)

    async def _handle_disconnected_device(
        self, device: AsyncMtiDevice, port: str
    ) -> None:
        device_info: MtiDeviceInfo = device.device_info()
        try:
            await device.close()
        except Exception as exc:
            logger.debug(f"{port}: error closing device: {exc}")

        if self._on_disconnect is not None:
            try:
                await self._on_disconnect(device_info)
            except Exception as exc:
                logger.warning(f"{port}: on_disconnect raised: {exc}")

    # --- Probe ---

    async def _probe_loop(self) -> None:
        while not self._stop_event.is_set():
            await self._run_probe_cycle()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._config.probe_interval,
                )
                break
            except asyncio.TimeoutError:
                pass

    async def _run_probe_cycle(self) -> None:
        async with self._lock:
            ports_to_probe: list[MtiPortInfo] = list(self._unprobed_ports)

        if not ports_to_probe:
            return

        probe_results: list[MtiProbeResult | None] = await asyncio.gather(
            *[
                asyncio.to_thread(probe_port, port_info, self._config.probe_timeout)
                for port_info in ports_to_probe
            ]
        )

        for probe_result in probe_results:
            if probe_result is not None:
                await self._handle_probe_result(probe_result)

    async def _handle_probe_result(self, probe_result: MtiProbeResult) -> None:
        port: str = probe_result.port_info.port
        try:
            communicator: AsyncMtiDeviceCommunicator = (
                await AsyncMtiDeviceCommunicator.create(
                    port_info=probe_result.port_info,
                    device_info=probe_result.device_info,
                    timeout=self._config.probe_timeout,
                )
            )
            device: AsyncMtiDevice = AsyncMtiDevice(communicator=communicator)
        except Exception as exc:
            logger.warning(f"{port}: failed to open device: {exc}")
            return

        device_id: MtiDeviceID = probe_result.device_info.device_id
        async with self._lock:
            self._unprobed_ports.discard(probe_result.port_info)
            self._devices[device_id] = device

        try:
            await self._on_connect(device)
        except Exception as exc:
            logger.warning(f"{port}: on_connect raised: {exc}")
