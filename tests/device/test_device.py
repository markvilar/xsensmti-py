"""
Unit tests for MtiDevice.update() callback dispatch.

MtiDeviceCommunicator is mocked so no serial port is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from xsensmti.device import (
    MtiDevice,
    MtiDeviceCommunicator,
    MtiDeviceID,
    MtiMessage,
)
from xsensmti.xbus import (
    XbusFraming,
    XbusMessage,
    XbusMessageID,
    decode_xbus_messages_from_buffer,
)


def _make_frame(mid: XbusMessageID, payload: bytes = b"") -> bytes:
    body = bytes([0xFF, int(mid), len(payload)]) + payload
    checksum = (-sum(body)) & 0xFF
    return bytes([XbusFraming.PREAMBLE]) + body + bytes([checksum])


def _parse_message(mid: XbusMessageID, payload: bytes = b"") -> XbusMessage:
    messages = decode_xbus_messages_from_buffer(_make_frame(mid, payload))
    assert len(messages) == 1
    return messages[0]


def _make_device() -> MtiDevice:
    communicator = MagicMock(spec=MtiDeviceCommunicator)
    device_id = MtiDeviceID(
        device_id=0x12345678,
        product_code="MTi-700",
        firmware_version="1.0.0",
        hardware_version="2.0",
    )
    return MtiDevice(device_id=device_id, communicator=communicator)


class TestUpdateDispatch:
    def test_update_dispatches_single_message(self) -> None:
        device = _make_device()
        received: list[object] = []
        device.set_on_message(received.append)

        msg = _parse_message(XbusMessageID.MTDATA2, b"\x01\x02")
        device._on_message(msg)
        device.update()

        assert len(received) == 1

    def test_update_dispatches_multiple_messages_in_order(self) -> None:
        device = _make_device()
        received: list[XbusMessage] = []

        def callback(mti_message: MtiMessage) -> None:
            received.append(mti_message.xbus_message)

        device.set_on_message(callback)

        messages = [_parse_message(XbusMessageID.MTDATA2, bytes([i])) for i in range(3)]
        for message in messages:
            device._on_message(message)
        device.update()

        assert len(received) == 3
        for received_message, original in zip(received, messages):
            assert received_message.payload == original.payload

    def test_update_with_no_callback_does_not_raise(self) -> None:
        device = _make_device()
        msg = _parse_message(XbusMessageID.MTDATA2)
        device._on_message(msg)
        device.update()

    def test_update_clears_buffer(self) -> None:
        device = _make_device()
        call_count = 0

        def callback(_: object) -> None:
            nonlocal call_count
            call_count += 1

        device.set_on_message(callback)

        msg = _parse_message(XbusMessageID.MTDATA2)
        device._on_message(msg)
        device.update()
        device.update()

        assert call_count == 1
