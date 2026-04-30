"""Read a binary file and parse Xbus messages."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import BinaryIO

import click

from loguru import logger

from xsens.xbus import XbusMessage
from xsens.xbus import decode_xbus_messages_from_buffer


def iter_chunks(path: Path, chunk_size: int) -> Generator[bytes, None, None]:
    with path.open("rb") as handle:
        stream: BinaryIO = handle
        while True:
            chunk: bytes = stream.read(chunk_size)
            if not chunk:
                break
            yield chunk


@click.command()
@click.argument(
    "input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--chunk-size",
    type=click.IntRange(min=1),
    default=4096,
    show_default=True,
    help="Chunk size to read in bytes.",
)
def main(
    input_path: Path,
    chunk_size: int,
) -> None:
    # Read chunks from binary file
    chunks: list[bytes] = [chunk for chunk in iter_chunks(input_path, chunk_size)]

    # Convert chunks into a bytearray
    buffer: bytearray = bytearray()
    for chunk in chunks:
        buffer.extend(chunk)

    messages: list[XbusMessage] = decode_xbus_messages_from_buffer(buffer)

    logger.info(f"Buffer length: {len(buffer)}")
    logger.info(f"Xbus messages: {len(messages)}")

    for message in messages[:5]:
        logger.info(message)


if __name__ == "__main__":
    main()
