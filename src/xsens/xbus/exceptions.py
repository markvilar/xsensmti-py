"""
Exceptions raised while parsing Xbus messages.
"""


class MissingHeader(Exception):
    """Raised when the buffer is too short to contain a header."""

    pass


class MissingChecksum(Exception):
    """Raised when the frame is too short to contain a checksum."""

    pass


class InvalidPreamble(Exception):
    """Raised when a frame does not start with a valid preamble."""

    pass


class InvalidPayloadLength(Exception):
    """Raised when the payload length fields are invalid or inconsistent."""

    pass


class IncompletePayload(Exception):
    """Raised when the frame does not contain the full payload."""

    pass


class InvalidChecksum(Exception):
    """Raised when a parsed message has an invalid checksum."""

    pass


class InvalidMessageID(Exception):
    """Raised when the MID byte does not correspond to a known MessageID."""

    def __init__(self, mid: int) -> None:
        self.mid = mid
        super().__init__(f"unknown message ID: {mid:#04x}")
