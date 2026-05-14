"""
Read and display live data from an XSens MTi sensor using MtiSession.

Opens the device, enters measurement mode, and prints decoded MTData2
readings to stdout until Ctrl-C is pressed.
"""

from __future__ import annotations

import click

from loguru import logger

from xsensmti.mtdata2 import Reading, decode_reading, decode_mtdata2_packets_from_message
from xsensmti.mtdata2 import OutputDataPacket
from xsensmti.port import MtiPortInfo
from xsensmti.session import MtiSession
from xsensmti.xbus.datatypes import XbusMessage


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
        logger.info(
            f"Device ID: {device.device_id():#010x}  "
            f"Product: {device.product_code() or '(unknown)'}  "
            f"FW: {device.firmware_version()}  HW: {device.hardware_version()}"
        )

        device.goto_measurement()
        logger.info("Streaming — press Ctrl-C to stop.")

        received: int = 0
        try:
            while count == 0 or received < count:
                msg: XbusMessage | None = device.take_first_data_packet_in_queue()
                if msg is None:
                    continue

                packets: list[OutputDataPacket] = decode_mtdata2_packets_from_message(msg)
                readings: list[Reading] = []
                for pkt in packets:
                    try:
                        readings.append(decode_reading(pkt))
                    except Exception:
                        pass

                if readings:
                    summary: str = "  ".join(_format_reading(r) for r in readings)
                    click.echo(f"[{received}] {summary}")

                received += 1
        except KeyboardInterrupt:
            pass

        logger.info(f"Received {received} packets.")


def _format_reading(reading: Reading) -> str:
    return repr(reading)


if __name__ == "__main__":
    main()
