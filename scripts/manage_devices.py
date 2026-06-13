"""
Discover and monitor XSens MTi devices using MtiDeviceManager.

Scans all serial ports at a configurable interval. Logs when devices are
discovered or disconnected. Press Ctrl-C to stop.
"""

from __future__ import annotations

import time

import click

from loguru import logger
from xsensmti.device import (
    MtiDevice,
    MtiDeviceInfo,
    MtiDeviceManager,
    MtiDeviceManagerConfig,
)


@click.command()
@click.option("--baud", default=115200, show_default=True, help="Baud rate.")
@click.option(
    "--scan-interval",
    default=2.0,
    show_default=True,
    help="Seconds between port scans.",
)
@click.option(
    "--probe-interval",
    default=1.0,
    show_default=True,
    help="Seconds between probe cycles.",
)
@click.option(
    "--probe-timeout",
    default=5.0,
    show_default=True,
    help="Seconds to wait for each device response during probing.",
)
def main(baud: int, scan_interval: float, probe_interval: float, probe_timeout: float) -> None:
    """Discover and monitor XSens MTi devices on all serial ports."""

    def on_connect(device: MtiDevice) -> None:
        info: MtiDeviceInfo = device.device_info()
        logger.info(
            f"Connected: {info.product_code or '(unknown)'}  "
            f"ID: {info.device_id:#010x}  "
            f"FW: {info.firmware_version}  HW: {info.hardware_version}"
        )

    def on_disconnect(device_info: MtiDeviceInfo) -> None:
        logger.info(
            f"Disconnected: {device_info.product_code or '(unknown)'}  "
            f"ID: {device_info.device_id:#010x}"
        )

    manager: MtiDeviceManager = MtiDeviceManager(
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        config=MtiDeviceManagerConfig(
            scan_interval=scan_interval,
            probe_interval=probe_interval,
            baud=baud,
            probe_timeout=probe_timeout,
        ),
    )

    logger.info(
        f"Scanning for devices (interval: {scan_interval}s) — press Ctrl-C to stop."
    )

    with manager:
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    logger.info("Stopped.")


if __name__ == "__main__":
    main()
