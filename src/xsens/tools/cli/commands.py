"""
CLI entry point for XSens MTi sensor tools.
"""

from __future__ import annotations

import sys

import click
from loguru import logger

from ..configurator.presets import PRESET_NAMES
from .actions import (
    dispatch_configure_device,
    dispatch_record_device,
    dispatch_scan_devices,
)


@click.group()
@click.option("--verbose", is_flag=True, default=False, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Command-line tools for XSens MTi sensors."""
    ctx.ensure_object(dict)
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


@main.command()
@click.option(
    "--baud", type=int, default=115200, show_default=True, help="Baud rate to probe."
)
@click.option(
    "--timeout",
    type=float,
    default=2.0,
    show_default=True,
    help="Per-port probe timeout in seconds.",
)
@click.option(
    "--usb-only", is_flag=True, default=False, help="Only probe ports with a USB VID."
)
def scan(baud: int, timeout: float, usb_only: bool) -> None:
    """Scan serial ports and report connected MTi devices."""
    dispatch_scan_devices(baud=baud, timeout=timeout, usb_only=usb_only)


@main.command()
@click.argument("port")
@click.option(
    "--preset",
    type=click.Choice(list(PRESET_NAMES)),
    default="gnss",
    show_default=True,
    help="Output data preset.",
)
@click.option(
    "--rate", type=int, default=100, show_default=True, help="Output data rate in Hz."
)
@click.option(
    "--baud", type=int, default=115200, show_default=True, help="Serial port baud rate."
)
@click.option(
    "--timeout",
    type=float,
    default=5.0,
    show_default=True,
    help="Per-command timeout in seconds.",
)
def configure(port: str, preset: str, rate: int, baud: int, timeout: float) -> None:
    """Configure an MTi device at PORT with a named output preset."""
    dispatch_configure_device(
        port=port, preset_name=preset, rate=rate, baud=baud, timeout=timeout
    )


@main.command()
@click.argument("port")
@click.argument("output")
@click.option(
    "--baud", type=int, default=115200, show_default=True, help="Serial port baud rate."
)
@click.option(
    "--timeout",
    type=float,
    default=5.0,
    show_default=True,
    help="Per-command handshake timeout in seconds.",
)
@click.option(
    "--chunk-size",
    type=int,
    default=4096,
    show_default=True,
    help="Read chunk size in bytes.",
)
def record(port: str, output: str, baud: int, timeout: float, chunk_size: int) -> None:
    """Record raw binary output from an MTi device at PORT to OUTPUT."""
    dispatch_record_device(
        port=port, output=output, baud=baud, timeout=timeout, chunk_size=chunk_size
    )


if __name__ == "__main__":
    main()
