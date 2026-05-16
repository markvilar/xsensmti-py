"""Read a binary file and parse Xbus and MTData2 messages."""

from __future__ import annotations

import click

from pathlib import Path
from loguru import logger
from xsensmti.mtdata2 import (
    OutputDataPacket,
    decode_mtdata2_packets_from_message,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    decode_xbus_messages_from_buffer,
)


@click.command()
@click.argument(
    "input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
def main(input_path: Path) -> None:
    buffer: bytes = input_path.read_bytes()
    logger.info(f"Read {len(buffer)} bytes from {input_path}")

    messages: list[XbusMessage] = decode_xbus_messages_from_buffer(buffer)
    logger.info(f"Decoded {len(messages)} Xbus messages")

    mtdata2_messages: list[XbusMessage] = [
        m for m in messages if m.header.mid == XbusMessageID.MTDATA2
    ]
    logger.info(f"MTData2 messages: {len(mtdata2_messages)}")

    for i, message in enumerate(mtdata2_messages):
        packets: list[OutputDataPacket] = decode_mtdata2_packets_from_message(message)
        packet_summary: str = ", ".join(p.data_id.name for p in packets)
        logger.info(f"[{i}] {len(packets)} packets: {packet_summary}")


if __name__ == "__main__":
    main()
