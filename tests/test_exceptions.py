"""
Tests for MtiDeviceError parsing of Xbus ERROR message payloads.
"""

from xsensmti.exceptions import MtiDeviceError
from xsensmti.xbus import XbusErrorCode


def test_error_parses_known_code() -> None:
    error = MtiDeviceError.from_payload(bytes([0x04]))
    assert error.code == XbusErrorCode.INVALID_MESSAGE
    assert error.data == b""


def test_error_message_describes_code() -> None:
    error = MtiDeviceError.from_payload(bytes([0x21]))
    assert "0x21" in str(error)
    assert "parameter sent is invalid or not within range" in str(error)


def test_error_preserves_unknown_code() -> None:
    error = MtiDeviceError.from_payload(bytes([0x99]))
    assert error.code == 0x99
    assert not isinstance(error.code, XbusErrorCode)
    assert "unknown error" in str(error)


def test_error_keeps_trailing_data() -> None:
    error = MtiDeviceError.from_payload(bytes([0x28, 0x01, 0x02, 0x03, 0x04, 0x05]))
    assert error.code == XbusErrorCode.DEVICE_ERROR
    assert error.data == bytes([0x01, 0x02, 0x03, 0x04, 0x05])


def test_error_from_device_payload() -> None:
    """The payload an MTi-G-700 actually returns for an unknown MID."""
    error = MtiDeviceError.from_payload(bytes.fromhex("0400000000"))
    assert error.code == XbusErrorCode.INVALID_MESSAGE
    assert error.data == bytes.fromhex("00000000")
