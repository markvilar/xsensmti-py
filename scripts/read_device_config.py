"""
Read and display configuration from an XSens MTi sensor.

Connects to the device in config mode and queries the device config,
filter profile, output configuration, and option flags, then prints
a summary to stdout.
"""

from __future__ import annotations

import dataclasses

import click

from loguru import logger
from xsensmti.device import (
    MtiDeviceConfig,
    MtiDeviceFilterProfile,
    MtiDeviceInfo,
    MtiDeviceOptions,
    MtiDeviceOutputConfig,
)
from xsensmti.port import MtiPortInfo
from xsensmti.device import MtiSession


@click.command()
@click.argument("port")
@click.option("--baud", default=115200, show_default=True, help="Baud rate.")
@click.option(
    "--timeout",
    default=5.0,
    show_default=True,
    help="Device handshake timeout in seconds.",
)
def main(port: str, baud: int, timeout: float) -> None:
    """Read and display configuration from an XSens MTi device on PORT."""
    port_info: MtiPortInfo = MtiPortInfo(port=port, baud=baud)

    with MtiSession(port_info, timeout=timeout) as device:
        info: MtiDeviceInfo = device.device_info()
        logger.info(
            f"Connected: {info.product_code or '(unknown)'}  "
            f"ID: {info.device_id:#010x}  "
            f"FW: {info.firmware_version}  HW: {info.hardware_version}"
        )
        _print_identity(info)
        _print_config(device.request_config())
        _print_filter_profile(device.request_filter_profile())
        _print_output_config(device.output_config())
        _print_options(device.request_options())


def _print_identity(info: MtiDeviceInfo) -> None:
    click.echo("\n--- Device ---")
    click.echo(f"  ID:       {info.device_id:#010x}")
    click.echo(f"  Product:  {info.product_code or '(unknown)'}")
    click.echo(f"  Firmware: {info.firmware_version}")
    click.echo(f"  Hardware: {info.hardware_version}")


def _print_config(config: MtiDeviceConfig) -> None:
    click.echo("\n--- Configuration ---")
    click.echo(f"  Devices:            {config.num_devices}")
    click.echo(
        f"  Sampling period:    {config.sampling_period if config.sampling_period is not None else 'n/a'}"
    )
    click.echo(
        f"  Output skip factor: {config.output_skip_factor if config.output_skip_factor is not None else 'n/a'}"
    )
    click.echo(
        f"  Output mode:        {config.output_mode if config.output_mode is not None else 'n/a'}"
    )
    click.echo(
        f"  Output settings:    {config.output_settings if config.output_settings is not None else 'n/a'}"
    )


def _print_filter_profile(profile: MtiDeviceFilterProfile) -> None:
    click.echo("\n--- Filter Profile ---")
    if profile.label:
        click.echo(f"  Label:   {profile.label}")
    else:
        click.echo(f"  Version: {profile.version}")
        click.echo(f"  Index:   {profile.index}")


def _print_output_config(config: MtiDeviceOutputConfig) -> None:
    click.echo("\n--- Output Configuration ---")
    if not config:
        click.echo("  (none)")
        return
    for odi, rate in config:
        click.echo(f"  {odi.name:<40} {rate} Hz")


def _print_options(options: MtiDeviceOptions) -> None:
    click.echo("\n--- Options ---")
    for field in dataclasses.fields(options):
        value: bool = getattr(options, field.name)
        click.echo(f"  {field.name:<45} {value}")


if __name__ == "__main__":
    main()
