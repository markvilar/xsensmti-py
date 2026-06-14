"""
Read and display live data from an XSens MTi sensor using AsyncMtiDeviceCommunicator.

Probes the port, enters measurement mode, and prints decoded MTData2 readings
to stdout until Ctrl-C is pressed.
"""

from __future__ import annotations

import asyncio
import signal

import click

from loguru import logger
from xsensmti.device import MtiDeviceInfo, MtiMessage, MtiPortInfo
from xsensmti.device.async_communicator import AsyncMtiDeviceCommunicator
from xsensmti.device.async_device import AsyncMtiDevice
from xsensmti.device.scanner import probe_port
from xsensmti.mtdata2 import (
    MtData2Packet,
    Reading,
    decode_mtdata2_packets_from_message,
    decode_reading,
)
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
    asyncio.run(_main(port, baud, timeout, count))


async def _main(port: str, baud: int, timeout: float, count: int) -> None:
    port_info: MtiPortInfo = MtiPortInfo(port=port, baud=baud)

    probe_result = await asyncio.to_thread(probe_port, port_info, timeout)
    if probe_result is None:
        logger.error(f"{port}: no MTi device found")
        return

    device_info: MtiDeviceInfo = probe_result.device_info
    logger.info(
        f"Device ID: {device_info.device_id:#010x}  "
        f"Product: {device_info.product_code or '(unknown)'}  "
        f"FW: {device_info.firmware_version}  HW: {device_info.hardware_version}"
    )

    communicator: AsyncMtiDeviceCommunicator = await AsyncMtiDeviceCommunicator.create(
        port_info=probe_result.port_info,
        device_info=probe_result.device_info,
        timeout=timeout,
    )
    device: AsyncMtiDevice = AsyncMtiDevice(communicator=communicator, timeout=timeout)

    received: int = 0
    stop_event: asyncio.Event = asyncio.Event()

    async def on_message(message: MtiMessage) -> None:
        nonlocal received
        if message.xbus_message.mid != XbusMessageID.MTDATA2:
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
        if count > 0 and received >= count:
            stop_event.set()

    device.set_on_message(on_message)

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)

    try:
        await device.goto_measurement()
        logger.info("Streaming — press Ctrl-C to stop.")
        await stop_event.wait()
    finally:
        await device.close()

    logger.info(f"Received {received} packets.")


def _format_reading(reading: Reading) -> str:
    return repr(reading)


if __name__ == "__main__":
    main()
