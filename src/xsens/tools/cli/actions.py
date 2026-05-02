"""
Actions that bridge CLI commands to the scanner and configurator tools.
"""

from __future__ import annotations

import serial

import click

from ..configurator import configure_device
from ..configurator.presets import OutputPreset, get_preset
from ..exceptions import (
    CommandTimeout,
    ConfigurationError,
    UnexpectedResponse,
    XsensToolsError,
)
from ..scanner import ScanResult, scan_ports


def dispatch_scan_devices(baud: int, timeout: float, usb_only: bool) -> None:
    """Call the scanner and echo found MTi devices to stdout."""
    results: list[ScanResult] = scan_ports(baud=baud, timeout=timeout, usb_only=usb_only)

    for result in results:
        label: str = f"  product={result.product_code}" if result.product_code else ""
        click.echo(
            f"{result.port}  device_id={result.device_id:#010x}  baud={result.baud}{label}"
        )

    if not results:
        click.echo("No MTi devices found.")


def dispatch_configure_device(
    port: str,
    preset_name: str,
    rate: int,
    baud: int,
    timeout: float,
) -> None:
    """Resolve the preset, configure the device, and echo the result."""
    try:
        output_preset: OutputPreset = get_preset(preset_name, rate)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)

    try:
        configure_device(port=port, baud=baud, preset=output_preset, timeout=timeout)
        click.echo(
            f"Done. {port} is now streaming with preset '{preset_name}' at {rate} Hz."
        )
    except (
        CommandTimeout,
        UnexpectedResponse,
        ConfigurationError,
        XsensToolsError,
    ) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except (OSError, serial.SerialException) as exc:
        click.echo(f"Could not open port {port}: {exc}", err=True)
        raise SystemExit(1)
