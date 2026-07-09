"""
Unit tests for MtiDevice.update() callback dispatch.

MtiDeviceCommunicator is mocked so no serial port is needed.
"""

from __future__ import annotations

import struct

import pytest
from unittest.mock import MagicMock

from xsensmti.device import (
    MtiDevice,
    MtiDeviceCommunicator,
    MtiDeviceInfo,
    MtiMessage,
    Sample,
)
from xsensmti.mtdata2 import (
    Acceleration,
    MtData2PacketID,
    OrientationQuaternion,
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
    communicator.device_info.return_value = MtiDeviceInfo(
        device_id=0x12345678,
        product_code="MTi-700",
        firmware_version="1.0.0",
        hardware_version="2.0",
    )
    return MtiDevice(communicator=communicator)


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


def _make_mtdata2_payload(*packets: tuple[MtData2PacketID, bytes]) -> bytes:
    result = b""
    for xdi, data in packets:
        result += int(xdi).to_bytes(2, "big") + bytes([len(data)]) + data
    return result


class TestMeasurementCallbackDispatch:
    def test_measurement_callback_fires_for_mtdata2(self) -> None:
        device = _make_device()
        received: list[Sample[OrientationQuaternion]] = []

        device.set_on_measurement(
            OrientationQuaternion,
            lambda sample: received.append(sample),
        )

        payload = _make_mtdata2_payload(
            (
                MtData2PacketID.ORIENTATION_QUATERNION,
                struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0),
            ),
        )
        device._on_message(_parse_message(XbusMessageID.MTDATA2, payload))
        device.update()

        assert len(received) == 1
        sample = received[0]
        assert isinstance(sample.payload, OrientationQuaternion)
        assert sample.payload.w == 1.0
        assert sample.header.device_id.device_id == 0x12345678

    def test_measurement_callback_not_fired_for_non_mtdata2(self) -> None:
        device = _make_device()
        received: list[object] = []

        device.set_on_measurement(
            OrientationQuaternion, lambda sample: received.append(sample)
        )

        device._on_message(_parse_message(XbusMessageID.GOTOCONFIG_ACK))
        device.update()

        assert len(received) == 0

    def test_multiple_measurement_types_dispatched(self) -> None:
        device = _make_device()
        quaternions: list[OrientationQuaternion] = []
        accelerations: list[Acceleration] = []

        device.set_on_measurement(
            OrientationQuaternion, lambda sample: quaternions.append(sample.payload)
        )
        device.set_on_measurement(
            Acceleration, lambda sample: accelerations.append(sample.payload)
        )

        payload = _make_mtdata2_payload(
            (
                MtData2PacketID.ORIENTATION_QUATERNION,
                struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0),
            ),
            (MtData2PacketID.ACCELERATION, struct.pack(">fff", 0.0, 0.0, 9.81)),
        )
        device._on_message(_parse_message(XbusMessageID.MTDATA2, payload))
        device.update()

        assert len(quaternions) == 1
        assert len(accelerations) == 1
        assert accelerations[0].z == pytest.approx(9.81, rel=1e-5)

    def test_measurement_callback_removed_with_none(self) -> None:
        device = _make_device()
        received: list[object] = []

        device.set_on_measurement(
            OrientationQuaternion, lambda sample: received.append(sample.payload)
        )
        device.set_on_measurement(OrientationQuaternion, None)

        payload = _make_mtdata2_payload(
            (
                MtData2PacketID.ORIENTATION_QUATERNION,
                struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0),
            ),
        )
        device._on_message(_parse_message(XbusMessageID.MTDATA2, payload))
        device.update()

        assert len(received) == 0

    def test_message_and_measurement_callbacks_coexist(self) -> None:
        device = _make_device()
        messages: list[object] = []
        measurements: list[object] = []

        device.set_on_message(lambda m: messages.append(m))
        device.set_on_measurement(
            OrientationQuaternion, lambda sample: measurements.append(sample.payload)
        )

        payload = _make_mtdata2_payload(
            (
                MtData2PacketID.ORIENTATION_QUATERNION,
                struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0),
            ),
        )
        device._on_message(_parse_message(XbusMessageID.MTDATA2, payload))
        device.update()

        assert len(messages) == 1
        assert len(measurements) == 1

    def test_unregistered_measurement_type_not_dispatched(self) -> None:
        device = _make_device()
        received: list[object] = []

        device.set_on_measurement(
            OrientationQuaternion, lambda sample: received.append(sample.payload)
        )

        payload = _make_mtdata2_payload(
            (MtData2PacketID.ACCELERATION, struct.pack(">fff", 0.0, 0.0, 9.81)),
        )
        device._on_message(_parse_message(XbusMessageID.MTDATA2, payload))
        device.update()

        assert len(received) == 0
