"""
Replay a recorded binary file as fixed-size byte chunks.
"""

import click

from collections.abc import Generator
from pathlib import Path


def iter_chunks(path: Path, chunk_size: int) -> Generator[bytes, None, None]:
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def replay_chunks(
    input: Path,
    chunk_size: int,
    emit: str,
) -> None:
    """Replays byte chunks from a recording."""
    for chunk in iter_chunks(input, chunk_size):
        if emit == "raw":
            click.get_binary_stream("stdout").write(chunk)
        elif emit == "hex":
            click.echo(chunk.hex())
        else:
            click.echo(str(len(chunk)))


@click.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--chunk-size",
    type=click.IntRange(min=1),
    default=4096,
    show_default=True,
    help="Chunk size to read in bytes.",
)
@click.option(
    "--emit",
    type=click.Choice(["raw", "hex", "lengths"], case_sensitive=False),
    default="lengths",
    show_default=True,
    help="Output mode.",
)
def main(input: Path, chunk_size: int, emit: str) -> None:
    replay_chunks(input, chunk_size, emit)


if __name__ == "__main__":
    main()
