"""
CLI entry point for XSens MTi sensor tools.
"""

from __future__ import annotations

import sys

from collections.abc import Sequence

import serial
import serial.tools.list_ports
from serial.tools.list_ports_common import ListPortInfo

import click
from loguru import logger

from xsens.xbus.datatypes import MessageID, XbusMessage

from .exceptions import (
    CommandTimeout,
    ConfigurationError,
    DeviceNotFound,
    UnexpectedResponse,
    XsensToolsError,
)
from .presets import (
    PRESET_NAMES,
    OutputPreset,
    build_output_configuration_payload,
    get_preset,
)
from .serial_io import open_serial_port, send_and_receive


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
    ports: Sequence[ListPortInfo] = serial.tools.list_ports.comports()

    if usb_only:
        ports = [p for p in ports if p.vid is not None]

    if not ports:
        click.echo("No serial ports found.")
        return

    found: int = 0

    for port_info in ports:
        port_name: str = port_info.device
        ser: serial.Serial | None = None

        try:
            ser = open_serial_port(port_name, baud, read_timeout=0.1)
            ser.reset_input_buffer()

            send_and_receive(
                ser,
                MessageID.GOTOCONFIG,
                expected_mid=MessageID.GOTOCONFIG_ACK,
                timeout=timeout,
            )

            device_id_msg: XbusMessage = send_and_receive(
                ser,
                MessageID.REQ_DEVICE_ID,
                expected_mid=MessageID.DEVICE_ID,
                timeout=timeout,
            )
            device_id: int = int.from_bytes(device_id_msg.payload, "big")

            product_code: str = ""
            try:
                product_code_msg: XbusMessage = send_and_receive(
                    ser,
                    MessageID.REQ_PRODUCT_CODE,
                    expected_mid=MessageID.PRODUCT_CODE,
                    timeout=timeout,
                )
                product_code = product_code_msg.payload.rstrip(b"\x00").decode(
                    "ascii", errors="replace"
                )
            except (CommandTimeout, UnexpectedResponse):
                pass

            label: str = f"  product={product_code}" if product_code else ""
            click.echo(f"{port_name}  device_id={device_id:#010x}  baud={baud}{label}")
            found += 1

        except (CommandTimeout, UnexpectedResponse, DeviceNotFound):
            logger.debug(f"{port_name}: no MTi device found")
        except (OSError, serial.SerialException) as exc:
            logger.debug(f"{port_name}: could not open port: {exc}")
        finally:
            if ser is not None:
                ser.close()

    if found == 0:
        click.echo("No MTi devices found.")


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
    try:
        output_preset: OutputPreset = get_preset(preset, rate)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)

    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, baud, read_timeout=0.1)
        ser.reset_input_buffer()

        logger.info(f"Entering configuration mode on {port}...")
        send_and_receive(
            ser,
            MessageID.GOTOCONFIG,
            expected_mid=MessageID.GOTOCONFIG_ACK,
            timeout=timeout,
        )

        device_id_msg: XbusMessage = send_and_receive(
            ser,
            MessageID.REQ_DEVICE_ID,
            expected_mid=MessageID.DEVICE_ID,
            timeout=timeout,
        )
        device_id: int = int.from_bytes(device_id_msg.payload, "big")
        logger.info(f"Device ID: {device_id:#010x}")

        payload: bytes = build_output_configuration_payload(output_preset)
        logger.info(
            f"Applying preset '{preset}' at {rate} Hz ({len(output_preset)} outputs)..."
        )
        send_and_receive(
            ser,
            MessageID.OUTPUT_CONFIGURATION,
            payload=payload,
            expected_mid=MessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=timeout,
        )

        logger.info("Entering measurement mode...")
        send_and_receive(
            ser,
            MessageID.GOTOMEASUREMENT,
            expected_mid=MessageID.GOTOMEASUREMENT_ACK,
            timeout=timeout,
        )

        click.echo(
            f"Done. {port} is now streaming with preset '{preset}' at {rate} Hz."
        )

    except (
        CommandTimeout,
        UnexpectedResponse,
        ConfigurationError,
        XsensToolsError,
    ) as exception:
        click.echo(f"Error: {exception}", err=True)
        raise SystemExit(1)
    except (OSError, serial.SerialException) as exception:
        click.echo(f"Could not open port {port}: {exception}", err=True)
        raise SystemExit(1)
    finally:
        if ser is not None:
            ser.close()


if __name__ == "__main__":
    main()
