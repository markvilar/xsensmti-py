"""
Integration tests replaying a real MTi binary recording end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xsensmti.xbus import (
    XbusMessageID,
    decode_xbus_messages_from_buffer,
)
from xsensmti.mtdata2 import (
    Acceleration,
    GnssPvt,
    MtData2PacketID,
    OrientationQuaternion,
    PacketCounter,
    RateOfTurn,
    SampleTimeFine,
    StatusWord,
    decode_all_readings,
    decode_mtdata2_packets_from_message,
)

_RECORDING = (
    Path(__file__).parent.parent.parent
    / "data"
    / "recordings"
    / "20260503_204234_xsensmti_with_gnss_recording.bin"
)

_IMU_PACKET_IDS = frozenset(
    {
        MtData2PacketID.PACKET_COUNTER,
        MtData2PacketID.SAMPLE_TIME_FINE,
        MtData2PacketID.ORIENTATION_QUATERNION,
        MtData2PacketID.ACCELERATION,
        MtData2PacketID.RATE_OF_TURN,
        MtData2PacketID.STATUS_WORD,
    }
)

_GNSS_PACKET_IDS = frozenset(
    {
        MtData2PacketID.PACKET_COUNTER,
        MtData2PacketID.SAMPLE_TIME_FINE,
        MtData2PacketID.GNSS_PVT,
    }
)

_EXPECTED_SHAPES = {_IMU_PACKET_IDS, _GNSS_PACKET_IDS}


@pytest.fixture(scope="module")
def mtdata2_messages():
    data = _RECORDING.read_bytes()
    all_messages = decode_xbus_messages_from_buffer(data)
    return [m for m in all_messages if m.header.mid == XbusMessageID.MTDATA2]


class TestRecordingReplay:
    def test_recording_contains_messages(self, mtdata2_messages) -> None:
        assert len(mtdata2_messages) > 0

    def test_each_message_has_expected_packet_ids(self, mtdata2_messages) -> None:
        for message in mtdata2_messages:
            packet_ids = frozenset(
                p.data_id for p in decode_mtdata2_packets_from_message(message)
            )
            assert packet_ids in _EXPECTED_SHAPES

    def test_all_readings_decode_without_error(self, mtdata2_messages) -> None:
        for message in mtdata2_messages:
            readings = decode_all_readings(message)
            assert len(readings) > 0

    def test_packet_counter_is_monotonically_increasing(self, mtdata2_messages) -> None:
        counters = []
        for message in mtdata2_messages:
            for reading in decode_all_readings(message):
                if isinstance(reading, PacketCounter):
                    counters.append(reading.counter)
        assert all(b > a for a, b in zip(counters, counters[1:]))

    def test_imu_reading_types_match_expected(self, mtdata2_messages) -> None:
        imu_message = next(
            m
            for m in mtdata2_messages
            if frozenset(p.data_id for p in decode_mtdata2_packets_from_message(m))
            == _IMU_PACKET_IDS
        )
        types = {type(reading) for reading in decode_all_readings(imu_message)}
        assert types == {
            PacketCounter,
            SampleTimeFine,
            OrientationQuaternion,
            Acceleration,
            RateOfTurn,
            StatusWord,
        }

    def test_gnss_reading_types_match_expected(self, mtdata2_messages) -> None:
        gnss_message = next(
            m
            for m in mtdata2_messages
            if frozenset(p.data_id for p in decode_mtdata2_packets_from_message(m))
            == _GNSS_PACKET_IDS
        )
        types = {type(reading) for reading in decode_all_readings(gnss_message)}
        assert types == {PacketCounter, SampleTimeFine, GnssPvt}
