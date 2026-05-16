"""
Exceptions raised while parsing MTData2 packets.
"""


class TruncatedPacket(Exception):
    """Raised when the payload ends before a declared packet's data is complete."""

    pass


class InvalidReadingData(Exception):
    """Raised when a packet's data bytes do not match the expected length for its XDI."""

    pass
