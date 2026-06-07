"""
MtiDeviceManager — automatic discovery and lifecycle management for multiple MTi devices.
"""

from __future__ import annotations

import threading

from collections.abc import Callable
from enum import StrEnum, auto
from loguru import logger
from xsensmti.device.datatypes import (
    MtiDeviceID,
    MtiDeviceInfo,
    MtiProbeResult,
)
from xsensmti.device.port import MtiPortInfo

from .communicator import MtiDeviceCommunicator
from .device import MtiDevice
from .scanner import probe_ports, scan_ports


type ConnectCallback = Callable[[MtiDevice], None]
type DisconnectCallback = Callable[[MtiDeviceInfo], None]


class MtiPortState(StrEnum):
    EMPTY = auto()
    ACTIVE = auto()


class MtiDeviceManager:
    """
    Discovers and manages the lifecycle of multiple connected MTi devices.

    Runs a background thread that periodically scans for serial ports and
    probes newly appeared ports for MTi devices. Fires callbacks when devices
    connect or disconnect.

    Attributes
    ----------
    on_connect: Called on the scan thread when a new device is found and opened.
    on_disconnect: Called on the scan thread when an active device disappears.
    scan_interval: Seconds between scan cycles.
    baud: Baud rate used when opening device ports.
    probe_timeout: Seconds to wait for each Xbus response during probing.
    """

    def __init__(
        self,
        on_connect: ConnectCallback,
        on_disconnect: DisconnectCallback | None = None,
        scan_interval: float = 5.0,
        baud: int = 115200,
        probe_timeout: float = 5.0,
    ) -> None:
        self._on_connect: ConnectCallback = on_connect
        self._on_disconnect: DisconnectCallback | None = on_disconnect
        self._scan_interval: float = scan_interval
        self._baud: int = baud
        self._probe_timeout: float = probe_timeout

        self._lock: threading.Lock = threading.Lock()
        self._port_states: dict[str, MtiPortState] = dict()
        self._devices: dict[MtiDeviceID, MtiDevice] = dict()
        self._probe_results: dict[MtiDeviceID, MtiProbeResult] = dict()

        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()

    def start(self) -> None:
        """Start the background scan loop."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scan loop and close all open devices."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        with self._lock:
            devices = list(self._devices.values())
            self._devices.clear()
            self._port_states.clear()
        for device in devices:
            try:
                device.close()
            except Exception as exc:
                logger.debug(f"error closing device on stop: {exc}")

    def update(self) -> None:
        """Drain message buffers of all active devices and dispatch their callbacks."""
        with self._lock:
            devices = list(self._devices.values())
        for device in devices:
            device.update()

    def devices(self) -> list[MtiDevice]:
        """Return a snapshot of currently active devices."""
        with self._lock:
            return list(self._devices.values())

    def get_device_info(self, device_id: MtiDeviceID) -> MtiDeviceInfo | None:
        """
        Return the device info for a known device ID, or None if not found.

        Arguments
        ---------
        device_id: Device ID to look up.

        Returns
        -------
        The MtiDeviceInfo from the probe result, or None.
        """
        with self._lock:
            probe_result = self._probe_results.get(device_id)
        return probe_result.device_info if probe_result is not None else None

    def get_port_info(self, device_id: MtiDeviceID) -> MtiPortInfo | None:
        """
        Return the port info for a known device ID, or None if not found.

        Arguments
        ---------
        device_id: Device ID to look up.

        Returns
        -------
        The MtiPortInfo from the probe result, or None.
        """
        with self._lock:
            probe_result = self._probe_results.get(device_id)
        return probe_result.port_info if probe_result is not None else None

    def __enter__(self) -> MtiDeviceManager:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    # --- Internal ---

    def _scan_loop(self) -> None:
        while True:
            self._run_scan_cycle()
            if self._stop_event.wait(self._scan_interval):
                break

    def _run_scan_cycle(self) -> None:
        scan_results = scan_ports(baud=self._baud)
        current_ports = {result.port_info.port for result in scan_results}

        with self._lock:
            known_ports = set(self._port_states.keys())

        disappeared_ports = known_ports - current_ports
        appeared_ports = current_ports - known_ports

        for port in disappeared_ports:
            self._handle_disappeared_port(port)

        port_infos_to_probe: list[MtiPortInfo] = [
            result.port_info
            for result in scan_results
            if result.port_info.port in appeared_ports
        ]

        if not port_infos_to_probe:
            return

        probe_results = probe_ports(port_infos_to_probe, timeout=self._probe_timeout)
        found_ports = {probe_result.port_info.port for probe_result in probe_results}

        for port_info in port_infos_to_probe:
            if port_info.port not in found_ports:
                with self._lock:
                    self._port_states[port_info.port] = MtiPortState.EMPTY

        for probe_result in probe_results:
            self._handle_new_device(probe_result)

    def _handle_disappeared_port(self, port: str) -> None:
        with self._lock:
            state = self._port_states.pop(port, None)

        if state != MtiPortState.ACTIVE:
            return

        with self._lock:
            device_id = next(
                (
                    did
                    for did, probe_result in self._probe_results.items()
                    if probe_result.port_info.port == port
                ),
                None,
            )
            device = (
                self._devices.pop(device_id, None) if device_id is not None else None
            )
            probe_result = (
                self._probe_results.get(device_id) if device_id is not None else None
            )

        if device is not None:
            try:
                device.close()
            except Exception as exc:
                logger.debug(f"{port}: error closing device: {exc}")

        if self._on_disconnect is not None and probe_result is not None:
            try:
                self._on_disconnect(probe_result.device_info)
            except Exception as exc:
                logger.warning(f"{port}: on_disconnect raised: {exc}")

    def _handle_new_device(self, probe_result: MtiProbeResult) -> None:
        port = probe_result.port_info.port
        try:
            communicator = MtiDeviceCommunicator(
                port_info=probe_result.port_info,
                device_info=probe_result.device_info,
                timeout=self._probe_timeout,
            )
            device = MtiDevice(communicator=communicator)
        except Exception as exc:
            logger.warning(f"{port}: failed to open device: {exc}")
            with self._lock:
                self._port_states[port] = MtiPortState.EMPTY
            return

        device_id = probe_result.device_info.device_id
        with self._lock:
            self._probe_results[device_id] = probe_result
            self._devices[device_id] = device
            self._port_states[port] = MtiPortState.ACTIVE

        try:
            self._on_connect(device)
        except Exception as exc:
            logger.warning(f"{port}: on_connect raised: {exc}")
