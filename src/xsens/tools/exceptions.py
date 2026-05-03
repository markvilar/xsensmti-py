"""
Exceptions raised by xsens.tools operations.
"""

from __future__ import annotations

from xsens.xbus.datatypes import MessageID


class XsensToolsError(Exception):
    """Base class for all xsens.tools errors."""


class DeviceNotFound(XsensToolsError):
    """Raised when no MTi device responds on the given port."""


class CommandTimeout(XsensToolsError):
    """Raised when the device does not respond within the timeout period."""

    def __init__(self, port: str, mid_sent: MessageID | int, timeout: float) -> None:
        self.port = port
        self.mid_sent = mid_sent
        self.timeout = timeout
        super().__init__(
            f"no response on {port} to MID {int(mid_sent):#04x} within {timeout}s"
        )


class UnexpectedResponse(XsensToolsError):
    """Raised when the device responds with a MID other than the expected ACK."""

    def __init__(
        self,
        expected: MessageID,
        received: MessageID,
    ) -> None:
        self.expected = expected
        self.received = received
        super().__init__(f"expected MID {int(expected):#04x}, got {int(received):#04x}")


class ConfigurationError(XsensToolsError):
    """Raised when the device rejects or NAKs a configuration command."""

    def __init__(self, mid: MessageID | int, detail: str) -> None:
        self.mid = mid
        self.detail = detail
        super().__init__(f"configuration failed for MID {int(mid):#04x}: {detail}")
