"""
Read and display live data from an XSens MTi sensor using MtiSession.

Opens the device, enters measurement mode, and prints decoded MTData2
readings to stdout until Ctrl-C is pressed.
"""

from __future__ import annotations

import click

from loguru import logger
from xsensmti.device import MtiDeviceInfo, MtiMessage
from xsensmti.mtdata2 import (
    MtData2Packet,
    Reading,
    decode_mtdata2_packets_from_message,
    decode_reading,
)
from xsensmti.port import MtiPortInfo
from xsensmti.device import MtiSession
from xsensmti.xbus import XbusMessageID


@click.command()
@click.argument("port")
@click.option("--baud", default=115200, show_default=True, help="Baud rate.")
@click.option(
    "--timeout",
    default=5.0,
    show_default=True,
    help="Device handshake timeout in seconds.",
)
@click.option(
    "--count",
    default=0,
    show_default=True,
    help="Number of packets to read (0 = unlimited).",
)
def main(port: str, baud: int, timeout: float, count: int) -> None:
    """Read live MTData2 packets from an XSens MTi device on PORT."""
    port_info: MtiPortInfo = MtiPortInfo(port=port, baud=baud)

    with MtiSession(port_info, timeout=timeout) as device:
        info: MtiDeviceInfo = device.device_info()
        logger.info(
            f"Device ID: {info.device_id:#010x}  "
            f"Product: {info.product_code or '(unknown)'}  "
            f"FW: {info.firmware_version}  HW: {info.hardware_version}"
        )

        received: int = 0

        def on_message(message: MtiMessage) -> None:
            nonlocal received
            if message.xbus_message.header.mid != XbusMessageID.MTDATA2:
                return

            packets: list[MtData2Packet] = decode_mtdata2_packets_from_message(
                message.xbus_message
            )
            readings: list[Reading] = []
            for packet in packets:
                try:
                    readings.append(decode_reading(packet))
                except Exception:
                    pass

            if readings:
                timestamp: str = message.header.timestamp.isoformat()
                summary: str = "  ".join(_format_reading(r) for r in readings)
                click.echo(f"[{received}] {timestamp}  {summary}")

            received += 1

        device.set_on_message(on_message)
        device.goto_measurement()
        logger.info("Streaming — press Ctrl-C to stop.")

        try:
            while count == 0 or received < count:
                device.update()
        except KeyboardInterrupt:
            pass

        logger.info(f"Received {received} packets.")


def _format_reading(reading: Reading) -> str:
    return repr(reading)


if __name__ == "__main__":
    main()
