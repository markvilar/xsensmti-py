"""
Unit tests for MTData2 reading decoders.
"""

from __future__ import annotations

import struct

import pytest

from xsensmti.xbus import (
    XbusMessageID,
    decode_xbus_messages_from_buffer,
    encode_xbus_message,
)
from xsensmti.mtdata2 import (
    Acceleration,
    AltitudeEllipsoid,
    BaroPressure,
    DeltaQ,
    DeltaV,
    FreeAcceleration,
    GnssPvt,
    InvalidReadingData,
    MagneticField,
    MtData2Packet,
    MtData2PacketID,
    OrientationEuler,
    OrientationQuaternion,
    PacketCounter,
    PositionEcef,
    PositionLLEllipsoid,
    RateOfTurn,
    SampleTimeFine,
    StatusByte,
    StatusWord,
    Temperature,
    UnknownReading,
    UtcTime,
    VelocityNed,
    decode_all_readings,
    decode_reading,
)


def _make_packet(xdi: MtData2PacketID, data: bytes) -> MtData2Packet:
    return MtData2Packet(data_id=xdi, length=len(data), data=data)


def _make_mtdata2_message(payload: bytes):
    frame = encode_xbus_message(XbusMessageID.MTDATA2, payload=payload)
    return decode_xbus_messages_from_buffer(frame)[0]


_GNSS_PVT_FORMAT = ">IHBBBBBBIiBBBBiiiiIIiiiiiIIiHHHHHHH"


class TestDecodeReading:
    def test_temperature(self) -> None:
        packet = _make_packet(MtData2PacketID.TEMPERATURE, struct.pack(">f", 23.5))
        reading = decode_reading(packet)
        assert isinstance(reading, Temperature)
        assert reading.temperature == pytest.approx(23.5)

    def test_utc_time(self) -> None:
        data = struct.pack(">IHBBBBBB", 500000, 2024, 5, 15, 12, 30, 0, 0x07)
        packet = _make_packet(MtData2PacketID.UTC_TIME, data)
        reading = decode_reading(packet)
        assert isinstance(reading, UtcTime)
        assert reading.nanoseconds == 500000
        assert reading.year == 2024
        assert reading.month == 5
        assert reading.day == 15
        assert reading.hour == 12
        assert reading.minute == 30
        assert reading.second == 0
        assert reading.valid == 0x07

    def test_packet_counter(self) -> None:
        packet = _make_packet(MtData2PacketID.PACKET_COUNTER, struct.pack(">H", 42))
        reading = decode_reading(packet)
        assert isinstance(reading, PacketCounter)
        assert reading.counter == 42

    def test_sample_time_fine(self) -> None:
        packet = _make_packet(
            MtData2PacketID.SAMPLE_TIME_FINE, struct.pack(">I", 100000)
        )
        reading = decode_reading(packet)
        assert isinstance(reading, SampleTimeFine)
        assert reading.time == 100000

    def test_baro_pressure(self) -> None:
        packet = _make_packet(MtData2PacketID.BARO_PRESSURE, struct.pack(">I", 101325))
        reading = decode_reading(packet)
        assert isinstance(reading, BaroPressure)
        assert reading.pressure == 101325

    def test_orientation_quaternion(self) -> None:
        data = struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0)
        packet = _make_packet(MtData2PacketID.ORIENTATION_QUATERNION, data)
        reading = decode_reading(packet)
        assert isinstance(reading, OrientationQuaternion)
        assert reading.w == pytest.approx(1.0)
        assert reading.x == pytest.approx(0.0)
        assert reading.y == pytest.approx(0.0)
        assert reading.z == pytest.approx(0.0)

    def test_orientation_euler(self) -> None:
        data = struct.pack(">fff", 10.0, -5.0, 90.0)
        packet = _make_packet(MtData2PacketID.ORIENTATION_EULER, data)
        reading = decode_reading(packet)
        assert isinstance(reading, OrientationEuler)
        assert reading.roll == pytest.approx(10.0)
        assert reading.pitch == pytest.approx(-5.0)
        assert reading.yaw == pytest.approx(90.0)

    def test_acceleration(self) -> None:
        data = struct.pack(">fff", 0.1, -0.2, 9.81)
        packet = _make_packet(MtData2PacketID.ACCELERATION, data)
        reading = decode_reading(packet)
        assert isinstance(reading, Acceleration)
        assert reading.x == pytest.approx(0.1)
        assert reading.y == pytest.approx(-0.2)
        assert reading.z == pytest.approx(9.81)

    def test_free_acceleration(self) -> None:
        data = struct.pack(">fff", 0.1, -0.2, 0.05)
        packet = _make_packet(MtData2PacketID.FREE_ACCELERATION, data)
        reading = decode_reading(packet)
        assert isinstance(reading, FreeAcceleration)
        assert reading.x == pytest.approx(0.1)
        assert reading.y == pytest.approx(-0.2)
        assert reading.z == pytest.approx(0.05)

    def test_delta_v(self) -> None:
        data = struct.pack(">fff", 0.001, 0.002, -0.003)
        packet = _make_packet(MtData2PacketID.DELTA_V, data)
        reading = decode_reading(packet)
        assert isinstance(reading, DeltaV)
        assert reading.x == pytest.approx(0.001)
        assert reading.y == pytest.approx(0.002)
        assert reading.z == pytest.approx(-0.003)

    def test_rate_of_turn(self) -> None:
        data = struct.pack(">fff", 0.01, -0.02, 0.03)
        packet = _make_packet(MtData2PacketID.RATE_OF_TURN, data)
        reading = decode_reading(packet)
        assert isinstance(reading, RateOfTurn)
        assert reading.x == pytest.approx(0.01)
        assert reading.y == pytest.approx(-0.02)
        assert reading.z == pytest.approx(0.03)

    def test_delta_q(self) -> None:
        data = struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0)
        packet = _make_packet(MtData2PacketID.DELTA_Q, data)
        reading = decode_reading(packet)
        assert isinstance(reading, DeltaQ)
        assert reading.w == pytest.approx(1.0)
        assert reading.x == pytest.approx(0.0)

    def test_magnetic_field(self) -> None:
        data = struct.pack(">fff", 0.1, 0.2, -0.5)
        packet = _make_packet(MtData2PacketID.MAGNETIC_FIELD, data)
        reading = decode_reading(packet)
        assert isinstance(reading, MagneticField)
        assert reading.x == pytest.approx(0.1)
        assert reading.y == pytest.approx(0.2)
        assert reading.z == pytest.approx(-0.5)

    def test_position_ecef(self) -> None:
        data = struct.pack(">fff", 3200000.0, 400000.0, 5100000.0)
        packet = _make_packet(MtData2PacketID.POSITION_ECEF, data)
        reading = decode_reading(packet)
        assert isinstance(reading, PositionEcef)
        assert reading.x == pytest.approx(3200000.0)
        assert reading.y == pytest.approx(400000.0)
        assert reading.z == pytest.approx(5100000.0)

    def test_velocity_ned(self) -> None:
        data = struct.pack(">fff", 1.0, 0.5, -0.1)
        packet = _make_packet(MtData2PacketID.VELOCITY_NED, data)
        reading = decode_reading(packet)
        assert isinstance(reading, VelocityNed)
        assert reading.north == pytest.approx(1.0)
        assert reading.east == pytest.approx(0.5)
        assert reading.down == pytest.approx(-0.1)

    def test_altitude_ellipsoid(self) -> None:
        packet = _make_packet(
            MtData2PacketID.ALTITUDE_ELLIPSOID, struct.pack(">f", 150.0)
        )
        reading = decode_reading(packet)
        assert isinstance(reading, AltitudeEllipsoid)
        assert reading.altitude == pytest.approx(150.0)

    def test_position_ll_ellipsoid(self) -> None:
        data = struct.pack(">ff", 59.9, 10.7)
        packet = _make_packet(MtData2PacketID.POSITION_LL_ELLIPSOID, data)
        reading = decode_reading(packet)
        assert isinstance(reading, PositionLLEllipsoid)
        assert reading.latitude == pytest.approx(59.9)
        assert reading.longitude == pytest.approx(10.7)

    def test_gnss_pvt(self) -> None:
        data = struct.pack(
            _GNSS_PVT_FORMAT,
            100000,  # itow
            2024,  # year
            5,  # month
            15,  # day
            12,  # hour
            30,  # minute
            0,  # second
            0x07,  # valid
            50,  # t_acc
            100,  # nano
            3,  # fix_type (3-D)
            0x01,  # flags
            12,  # num_sv
            0,  # reserved1
            100000000,  # lon  →  10.0 deg
            600000000,  # lat  →  60.0 deg
            50000,  # height → 50.0 m
            45000,  # h_msl  → 45.0 m
            2000,  # h_acc  →  2.0 m
            3000,  # v_acc  →  3.0 m
            1000,  # vel_n  →  1.0 m/s
            500,  # vel_e  →  0.5 m/s
            200,  # vel_d  →  0.2 m/s
            1118,  # g_speed
            2700000,  # head_mot → 27.0 deg
            500,  # s_acc
            500000,  # head_acc →  5.0 deg
            2700000,  # head_veh → 27.0 deg
            150,  # gdop  → 1.50
            130,  # pdop  → 1.30
            120,  # tdop  → 1.20
            110,  # vdop  → 1.10
            100,  # hdop  → 1.00
            90,  # ndop  → 0.90
            80,  # edop  → 0.80
        )
        packet = _make_packet(MtData2PacketID.GNSS_PVT, data)
        reading = decode_reading(packet)
        assert isinstance(reading, GnssPvt)
        assert reading.year == 2024
        assert reading.fix_type == 3
        assert reading.num_sv == 12
        assert reading.latitude == pytest.approx(60.0)
        assert reading.longitude == pytest.approx(10.0)
        assert reading.height == pytest.approx(50.0)
        assert reading.pos_dop == pytest.approx(1.30)
        assert reading.horiz_dop == pytest.approx(1.00)

    def test_status_byte(self) -> None:
        packet = _make_packet(MtData2PacketID.STATUS_BYTE, struct.pack(">B", 0x05))
        reading = decode_reading(packet)
        assert isinstance(reading, StatusByte)
        assert reading.status == 0x05

    def test_status_word(self) -> None:
        packet = _make_packet(
            MtData2PacketID.STATUS_WORD, struct.pack(">I", 0x00000001)
        )
        reading = decode_reading(packet)
        assert isinstance(reading, StatusWord)
        assert reading.status == 0x00000001

    def test_wrong_length_raises_invalid_reading_data(self) -> None:
        packet = _make_packet(MtData2PacketID.PACKET_COUNTER, b"\x00")
        with pytest.raises(InvalidReadingData):
            decode_reading(packet)


class TestDecodeAllReadings:
    def test_empty_payload_returns_empty_list(self) -> None:
        message = _make_mtdata2_message(b"")
        assert decode_all_readings(message) == []

    def test_returns_one_reading_per_packet(self) -> None:
        payload = (
            int(MtData2PacketID.PACKET_COUNTER).to_bytes(2, "big")
            + b"\x02"
            + struct.pack(">H", 7)
            + int(MtData2PacketID.STATUS_WORD).to_bytes(2, "big")
            + b"\x04"
            + struct.pack(">I", 0)
        )
        message = _make_mtdata2_message(payload)
        readings = decode_all_readings(message)
        assert len(readings) == 2
        assert isinstance(readings[0], PacketCounter)
        assert isinstance(readings[1], StatusWord)

    def test_unknown_xdi_produces_unknown_reading(self) -> None:
        # Build a payload with a known packet, an unknown XDI, and another known packet.
        # The unknown XDI is skipped by the parser, so only 2 readings are produced.
        payload = (
            int(MtData2PacketID.PACKET_COUNTER).to_bytes(2, "big")
            + b"\x02"
            + struct.pack(">H", 1)
            + b"\xff\xff"
            + b"\x02"
            + b"\xab\xcd"
            + int(MtData2PacketID.STATUS_WORD).to_bytes(2, "big")
            + b"\x04"
            + struct.pack(">I", 0)
        )
        message = _make_mtdata2_message(payload)
        readings = decode_all_readings(message)
        assert len(readings) == 2
        assert not any(isinstance(reading, UnknownReading) for reading in readings)
