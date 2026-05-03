"""
Exceptions raised while parsing MTData2 packets.
"""


class NotMTData2Message(Exception):
    """Raised when a message MID is not MTData2."""

    pass


class TruncatedPacket(Exception):
    """Raised when the payload ends before a declared packet's data is complete."""

    pass


class InvalidReadingData(Exception):
    """Raised when a packet's data bytes do not match the expected length for its XDI."""

    pass
