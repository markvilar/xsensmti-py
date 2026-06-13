"""
MtiDeviceManager — automatic discovery and lifecycle management for multiple MTi devices.
"""

from __future__ import annotations

import threading

from collections.abc import Callable
from dataclasses import dataclass
from loguru import logger
from xsensmti.device.datatypes import (
    MtiDeviceID,
    MtiDeviceInfo,
    MtiPortInfo,
    MtiProbeResult,
    MtiScanResult,
)

from .communicator import MtiDeviceCommunicator
from .device import MtiDevice
from .scanner import probe_ports, scan_ports


type ConnectCallback = Callable[[MtiDevice], None]
type DisconnectCallback = Callable[[MtiDeviceInfo], None]


@dataclass(frozen=True)
class MtiDeviceManagerConfig:
    """
    Tuning parameters for MtiDeviceManager.

    Attributes
    ----------
    scan_interval: Seconds between port scan cycles.
    probe_interval: Seconds between probe cycles.
    baud: Baud rate used when opening device ports.
    probe_timeout: Seconds to wait for each Xbus response during probing.
    """

    scan_interval: float = 2.0
    probe_interval: float = 1.0
    baud: int = 115200
    probe_timeout: float = 5.0


class MtiDeviceManager:
    """
    Discovers and manages the lifecycle of multiple connected MTi devices.

    Runs two background threads: a scan loop that detects port appearances and
    disappearances, and a probe loop that attempts to open unprobed ports as MTi
    devices. Fires callbacks when devices connect or disconnect. Ports that fail
    probing are retried on each probe cycle.

    Attributes
    ----------
    on_connect: Called on the probe thread when a new device is opened.
    on_disconnect: Called on the scan thread when an active device disappears.
    config: Tuning parameters for scanning and probing.
    """

    def __init__(
        self,
        on_connect: ConnectCallback,
        on_disconnect: DisconnectCallback | None = None,
        config: MtiDeviceManagerConfig = MtiDeviceManagerConfig(),
    ) -> None:
        self._on_connect: ConnectCallback = on_connect
        self._on_disconnect: DisconnectCallback | None = on_disconnect
        self._config: MtiDeviceManagerConfig = config

        self._lock: threading.Lock = threading.Lock()
        self._unprobed_ports: set[MtiPortInfo] = set()
        self._devices: dict[MtiDeviceID, MtiDevice] = dict()

        self._scan_thread: threading.Thread | None = None
        self._probe_thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()

    # --- Public API ---

    def start(self) -> None:
        """Start the background scan and probe loops."""
        self._stop_event.clear()
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._probe_thread = threading.Thread(target=self._probe_loop, daemon=True)
        self._scan_thread.start()
        self._probe_thread.start()

    def stop(self) -> None:
        """Stop both loops and close all open devices."""
        self._stop_event.set()
        if self._scan_thread is not None:
            self._scan_thread.join()
            self._scan_thread = None
        if self._probe_thread is not None:
            self._probe_thread.join()
            self._probe_thread = None
        with self._lock:
            devices: list[MtiDevice] = list(self._devices.values())
            self._devices.clear()
            self._unprobed_ports.clear()
        for device in devices:
            try:
                device.close()
            except Exception as exc:
                logger.debug(f"error closing device on stop: {exc}")

    def update(self) -> None:
        """Drain message buffers of all active devices and dispatch their callbacks."""
        for device in self.active_devices():
            device.update()

    def active_devices(self) -> list[MtiDevice]:
        """Return a snapshot of currently active devices."""
        with self._lock:
            return list(self._devices.values())

    def active_device_ids(self) -> list[MtiDeviceID]:
        """Return a snapshot of currently active device IDs."""
        with self._lock:
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
        with self._lock:
            device: MtiDevice | None = self._devices.get(device_id)
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
        with self._lock:
            device = self._devices.get(device_id)
        return device.port_info() if device is not None else None

    def __enter__(self) -> MtiDeviceManager:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    # --- Scan ---

    def _scan_loop(self) -> None:
        while True:
            self._run_scan_cycle()
            if self._stop_event.wait(self._config.scan_interval):
                break

    def _run_scan_cycle(self) -> None:
        scan_results: list[MtiScanResult] = scan_ports(baud=self._config.baud)
        current_port_infos: set[MtiPortInfo] = {r.port_info for r in scan_results}
        current_ports: set[str] = {pi.port for pi in current_port_infos}

        with self._lock:
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
            self._handle_disappeared_port(port)

        with self._lock:
            self._unprobed_ports.update(appeared_port_infos)

    def _handle_disappeared_port(self, port: str) -> None:
        with self._lock:
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
            device: MtiDevice | None = (
                self._devices.pop(device_id, None) if device_id is not None else None
            )

        if device is not None:
            self._handle_disconnected_device(device, port)

    def _handle_disconnected_device(self, device: MtiDevice, port: str) -> None:
        device_info: MtiDeviceInfo = device.device_info()
        try:
            device.close()
        except Exception as exc:
            logger.debug(f"{port}: error closing device: {exc}")

        if self._on_disconnect is not None:
            try:
                self._on_disconnect(device_info)
            except Exception as exc:
                logger.warning(f"{port}: on_disconnect raised: {exc}")

    # --- Probe ---

    def _probe_loop(self) -> None:
        while True:
            self._run_probe_cycle()
            if self._stop_event.wait(self._config.probe_interval):
                break

    def _run_probe_cycle(self) -> None:
        with self._lock:
            ports_to_probe: list[MtiPortInfo] = list(self._unprobed_ports)

        if not ports_to_probe:
            return

        probe_results: list[MtiProbeResult] = probe_ports(
            ports_to_probe, timeout=self._config.probe_timeout
        )

        for probe_result in probe_results:
            self._handle_probe_result(probe_result)

    def _handle_probe_result(self, probe_result: MtiProbeResult) -> None:
        port: str = probe_result.port_info.port
        try:
            communicator: MtiDeviceCommunicator = MtiDeviceCommunicator(
                port_info=probe_result.port_info,
                device_info=probe_result.device_info,
                timeout=self._config.probe_timeout,
            )
            device: MtiDevice = MtiDevice(communicator=communicator)
        except Exception as exc:
            logger.warning(f"{port}: failed to open device: {exc}")
            return

        device_id: MtiDeviceID = probe_result.device_info.device_id
        with self._lock:
            self._unprobed_ports.discard(probe_result.port_info)
            self._devices[device_id] = device

        try:
            self._on_connect(device)
        except Exception as exc:
            logger.warning(f"{port}: on_connect raised: {exc}")
