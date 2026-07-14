"""
Domain exceptions for the xsensmti library.
"""

from __future__ import annotations

from serial import SerialException as SerialException
from xsensmti.xbus import XbusErrorCode, XbusMessageID


class XsensError(Exception):
    """Base class for all xsensmti errors."""


class MtiDeviceError(XsensError):
    """
    Raised when the device replies with an Xbus ERROR message.

    Attributes:
        code: Error code sent by the device, or the raw int if it is not a known code.
        data: Any bytes following the error code (DEVICE_ERROR carries 5).
    """

    def __init__(self, code: XbusErrorCode | int, data: bytes = b"") -> None:
        self.code = code
        self.data = data
        super().__init__(f"device error {int(code):#04x}: {_describe(code)}")

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceError:
        """
        Parse an ERROR message payload into an MtiDeviceError.

        Args:
            payload: Payload of an Xbus ERROR message: an error code, optionally
                followed by further bytes.
        """
        raw_code: int = payload[0]
        code: XbusErrorCode | int
        try:
            code = XbusErrorCode(raw_code)
        except ValueError:
            code = raw_code
        return cls(code=code, data=payload[1:])


class DeviceNotFound(XsensError):
    """Raised when no MTi device responds on the given port."""


class CommandTimeout(XsensError):
    """Raised when the device does not respond within the timeout period."""

    def __init__(
        self, port: str, mid_sent: XbusMessageID | int, timeout: float
    ) -> None:
        self.port = port
        self.mid_sent = mid_sent
        self.timeout = timeout
        super().__init__(
            f"no response on {port} to MID {int(mid_sent):#04x} within {timeout}s"
        )


class UnexpectedResponse(XsensError):
    """Raised when the device responds with a MID other than the expected ACK."""

    def __init__(
        self,
        expected: XbusMessageID,
        received: XbusMessageID,
    ) -> None:
        self.expected = expected
        self.received = received
        super().__init__(f"expected MID {int(expected):#04x}, got {int(received):#04x}")


class ConfigurationError(XsensError):
    """Raised when the device rejects or NAKs a configuration command."""

    def __init__(self, mid: XbusMessageID | int, detail: str) -> None:
        self.mid = mid
        self.detail = detail
        super().__init__(f"configuration failed for MID {int(mid):#04x}: {detail}")


class UnexpectedXbusMessage(XsensError):
    """Raised when an XbusMessage has a MID that is not valid in the current context."""


def _describe(code: XbusErrorCode | int) -> str:
    if isinstance(code, XbusErrorCode):
        return _ERROR_CODE_DESCRIPTIONS[code]
    return "unknown error"


_ERROR_CODE_DESCRIPTIONS: dict[XbusErrorCode, str] = {
    XbusErrorCode.INVALID_PERIOD: "period sent is not within valid range",
    XbusErrorCode.INVALID_MESSAGE: "message sent is invalid",
    XbusErrorCode.TIMER_OVERFLOW: "timer overflow",
    XbusErrorCode.INVALID_BAUDRATE: "baud rate sent is not within valid range",
    XbusErrorCode.INVALID_PARAMETER: "parameter sent is invalid or not within range",
    XbusErrorCode.DEVICE_ERROR: "device error, try updating the firmware",
}
