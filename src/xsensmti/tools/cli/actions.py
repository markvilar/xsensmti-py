"""
Actions that bridge CLI commands to the scanner and configurator tools.
"""

from __future__ import annotations

import datetime
import click
import serial

from pathlib import Path
from xsensmti.exceptions import (
    CommandTimeout,
    ConfigurationError,
    UnexpectedResponse,
    XsensError,
)
from ..configurator import configure_device
from ..configurator.presets import (
    OutputPreset,
    get_preset,
)
from ..recorder import (
    RecordingResult,
    record_device,
)
from ..scanner import MtiScanResult, scan_ports


def dispatch_scan_devices(baud: int, timeout: float, usb_only: bool) -> None:
    """Call the scanner and echo found MTi devices to stdout."""
    results: list[MtiScanResult] = scan_ports(
        baud=baud, timeout=timeout, usb_only=usb_only
    )

    for result in results:
        label: str = f"  product={result.product_code}" if result.product_code else ""
        usb: str = (
            f"  {result.port_info.usb_info}"
            if result.port_info.usb_info is not None
            else ""
        )
        click.echo(
            f"{result.port_info.port}  device_id={result.device_id:#010x}  baud={result.port_info.baud}{label}{usb}"
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
        XsensError,
    ) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except (OSError, serial.SerialException) as exc:
        click.echo(f"Could not open port {port}: {exc}", err=True)
        raise SystemExit(1)


_DEFAULT_RECORDINGS_DIR: Path = Path("data/recordings")


def dispatch_record_device(
    port: str,
    output: str | None,
    baud: int,
    timeout: float,
    chunk_size: int,
) -> None:
    """Verify the device, record its output, and echo the session summary."""
    if output is None:
        timestamp: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path: Path = (
            _DEFAULT_RECORDINGS_DIR / f"{timestamp}_xsensmti_recording.bin"
        )
    else:
        output_path = Path(output)

    try:
        result: RecordingResult = record_device(
            port=port,
            output=output_path,
            baud=baud,
            timeout=timeout,
            chunk_size=chunk_size,
        )
        rate: float = (
            result.bytes_recorded / result.duration if result.duration > 0 else 0.0
        )
        click.echo(
            f"Recorded {result.bytes_recorded} bytes in {result.duration:.1f}s"
            f" ({rate:.0f} B/s) → {result.output_path}"
        )
    except (CommandTimeout, UnexpectedResponse, XsensError) as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except OSError as exc:
        click.echo(f"Could not open port {port}: {exc}", err=True)
        raise SystemExit(1)
    except serial.SerialException as exc:
        click.echo(f"Serial error on {port}: {exc}", err=True)
        raise SystemExit(1)
