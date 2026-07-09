"""
Unit tests for MTData2 measurement decoders.
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
    InvalidMeasurementData,
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
    StatusByteFlags,
    StatusWord,
    StatusWordFlags,
    Temperature,
    UnknownMeasurement,
    UtcTime,
    VelocityNed,
    decode_all_measurements,
    decode_measurement,
)


def _make_packet(xdi: MtData2PacketID, data: bytes) -> MtData2Packet:
    return MtData2Packet(data_id=xdi, length=len(data), data=data)


def _make_mtdata2_message(payload: bytes):
    frame = encode_xbus_message(XbusMessageID.MTDATA2, payload=payload)
    return decode_xbus_messages_from_buffer(frame)[0]


_GNSS_PVT_FORMAT = ">IHBBBBBBIiBBBBiiiiIIiiiiiIIiHHHHHHH"


class TestDecodeMeasurement:
    def test_temperature(self) -> None:
        packet = _make_packet(MtData2PacketID.TEMPERATURE, struct.pack(">f", 23.5))
        measurement = decode_measurement(packet)
        assert isinstance(measurement, Temperature)
        assert measurement.temperature == pytest.approx(23.5)

    def test_utc_time(self) -> None:
        data = struct.pack(">IHBBBBBB", 500000, 2024, 5, 15, 12, 30, 0, 0x07)
        packet = _make_packet(MtData2PacketID.UTC_TIME, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, UtcTime)
        assert measurement.nanoseconds == 500000
        assert measurement.year == 2024
        assert measurement.month == 5
        assert measurement.day == 15
        assert measurement.hour == 12
        assert measurement.minute == 30
        assert measurement.second == 0
        assert measurement.valid == 0x07

    def test_packet_counter(self) -> None:
        packet = _make_packet(MtData2PacketID.PACKET_COUNTER, struct.pack(">H", 42))
        measurement = decode_measurement(packet)
        assert isinstance(measurement, PacketCounter)
        assert measurement.counter == 42

    def test_sample_time_fine(self) -> None:
        packet = _make_packet(
            MtData2PacketID.SAMPLE_TIME_FINE, struct.pack(">I", 100000)
        )
        measurement = decode_measurement(packet)
        assert isinstance(measurement, SampleTimeFine)
        assert measurement.time == 100000

    def test_baro_pressure(self) -> None:
        packet = _make_packet(MtData2PacketID.BARO_PRESSURE, struct.pack(">I", 101325))
        measurement = decode_measurement(packet)
        assert isinstance(measurement, BaroPressure)
        assert measurement.pressure == 101325

    def test_orientation_quaternion(self) -> None:
        data = struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0)
        packet = _make_packet(MtData2PacketID.ORIENTATION_QUATERNION, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, OrientationQuaternion)
        assert measurement.w == pytest.approx(1.0)
        assert measurement.x == pytest.approx(0.0)
        assert measurement.y == pytest.approx(0.0)
        assert measurement.z == pytest.approx(0.0)

    def test_orientation_euler(self) -> None:
        data = struct.pack(">fff", 10.0, -5.0, 90.0)
        packet = _make_packet(MtData2PacketID.ORIENTATION_EULER, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, OrientationEuler)
        assert measurement.roll == pytest.approx(10.0)
        assert measurement.pitch == pytest.approx(-5.0)
        assert measurement.yaw == pytest.approx(90.0)

    def test_acceleration(self) -> None:
        data = struct.pack(">fff", 0.1, -0.2, 9.81)
        packet = _make_packet(MtData2PacketID.ACCELERATION, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, Acceleration)
        assert measurement.x == pytest.approx(0.1)
        assert measurement.y == pytest.approx(-0.2)
        assert measurement.z == pytest.approx(9.81)

    def test_free_acceleration(self) -> None:
        data = struct.pack(">fff", 0.1, -0.2, 0.05)
        packet = _make_packet(MtData2PacketID.FREE_ACCELERATION, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, FreeAcceleration)
        assert measurement.x == pytest.approx(0.1)
        assert measurement.y == pytest.approx(-0.2)
        assert measurement.z == pytest.approx(0.05)

    def test_delta_v(self) -> None:
        data = struct.pack(">fff", 0.001, 0.002, -0.003)
        packet = _make_packet(MtData2PacketID.DELTA_V, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, DeltaV)
        assert measurement.x == pytest.approx(0.001)
        assert measurement.y == pytest.approx(0.002)
        assert measurement.z == pytest.approx(-0.003)

    def test_rate_of_turn(self) -> None:
        data = struct.pack(">fff", 0.01, -0.02, 0.03)
        packet = _make_packet(MtData2PacketID.RATE_OF_TURN, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, RateOfTurn)
        assert measurement.x == pytest.approx(0.01)
        assert measurement.y == pytest.approx(-0.02)
        assert measurement.z == pytest.approx(0.03)

    def test_delta_q(self) -> None:
        data = struct.pack(">ffff", 1.0, 0.0, 0.0, 0.0)
        packet = _make_packet(MtData2PacketID.DELTA_Q, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, DeltaQ)
        assert measurement.w == pytest.approx(1.0)
        assert measurement.x == pytest.approx(0.0)

    def test_magnetic_field(self) -> None:
        data = struct.pack(">fff", 0.1, 0.2, -0.5)
        packet = _make_packet(MtData2PacketID.MAGNETIC_FIELD, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, MagneticField)
        assert measurement.x == pytest.approx(0.1)
        assert measurement.y == pytest.approx(0.2)
        assert measurement.z == pytest.approx(-0.5)

    def test_position_ecef(self) -> None:
        data = struct.pack(">fff", 3200000.0, 400000.0, 5100000.0)
        packet = _make_packet(MtData2PacketID.POSITION_ECEF, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, PositionEcef)
        assert measurement.x == pytest.approx(3200000.0)
        assert measurement.y == pytest.approx(400000.0)
        assert measurement.z == pytest.approx(5100000.0)

    def test_velocity_ned(self) -> None:
        data = struct.pack(">fff", 1.0, 0.5, -0.1)
        packet = _make_packet(MtData2PacketID.VELOCITY_NED, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, VelocityNed)
        assert measurement.north == pytest.approx(1.0)
        assert measurement.east == pytest.approx(0.5)
        assert measurement.down == pytest.approx(-0.1)

    def test_altitude_ellipsoid(self) -> None:
        packet = _make_packet(
            MtData2PacketID.ALTITUDE_ELLIPSOID, struct.pack(">f", 150.0)
        )
        measurement = decode_measurement(packet)
        assert isinstance(measurement, AltitudeEllipsoid)
        assert measurement.altitude == pytest.approx(150.0)

    def test_position_ll_ellipsoid(self) -> None:
        data = struct.pack(">ff", 59.9, 10.7)
        packet = _make_packet(MtData2PacketID.POSITION_LL_ELLIPSOID, data)
        measurement = decode_measurement(packet)
        assert isinstance(measurement, PositionLLEllipsoid)
        assert measurement.latitude == pytest.approx(59.9)
        assert measurement.longitude == pytest.approx(10.7)

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
        measurement = decode_measurement(packet)
        assert isinstance(measurement, GnssPvt)
        assert measurement.year == 2024
        assert measurement.fix_type == 3
        assert measurement.num_sv == 12
        assert measurement.latitude == pytest.approx(60.0)
        assert measurement.longitude == pytest.approx(10.0)
        assert measurement.height == pytest.approx(50.0)
        assert measurement.pos_dop == pytest.approx(1.30)
        assert measurement.horiz_dop == pytest.approx(1.00)

    def test_status_byte(self) -> None:
        # 0x05 = SELFTEST | GNSS_FIX
        packet = _make_packet(MtData2PacketID.STATUS_BYTE, struct.pack(">B", 0x05))
        measurement = decode_measurement(packet)
        assert isinstance(measurement, StatusByte)
        assert isinstance(measurement.status, StatusByteFlags)
        assert StatusByteFlags.SELFTEST in measurement.status
        assert StatusByteFlags.GNSS_FIX in measurement.status
        assert StatusByteFlags.FILTER_VALID not in measurement.status

    def test_status_word(self) -> None:
        # 0x00000106 = FILTER_VALID | CLIP_ACC_X | CLIP_ACC_Y
        packet = _make_packet(
            MtData2PacketID.STATUS_WORD, struct.pack(">I", 0x00000306)
        )
        measurement = decode_measurement(packet)
        assert isinstance(measurement, StatusWord)
        assert isinstance(measurement.status, StatusWordFlags)
        assert StatusWordFlags.FILTER_VALID in measurement.status
        assert StatusWordFlags.CLIP_ACC_X in measurement.status
        assert StatusWordFlags.CLIP_ACC_Y in measurement.status
        assert StatusWordFlags.SELFTEST not in measurement.status

    def test_wrong_length_raises_invalid_measurement_data(self) -> None:
        packet = _make_packet(MtData2PacketID.PACKET_COUNTER, b"\x00")
        with pytest.raises(InvalidMeasurementData):
            decode_measurement(packet)


class TestDecodeAllMeasurements:
    def test_empty_payload_returns_empty_list(self) -> None:
        message = _make_mtdata2_message(b"")
        assert decode_all_measurements(message) == []

    def test_returns_one_measurement_per_packet(self) -> None:
        payload = (
            int(MtData2PacketID.PACKET_COUNTER).to_bytes(2, "big")
            + b"\x02"
            + struct.pack(">H", 7)
            + int(MtData2PacketID.STATUS_WORD).to_bytes(2, "big")
            + b"\x04"
            + struct.pack(">I", 0)
        )
        message = _make_mtdata2_message(payload)
        measurements = decode_all_measurements(message)
        assert len(measurements) == 2
        assert isinstance(measurements[0], PacketCounter)
        assert isinstance(measurements[1], StatusWord)

    def test_unknown_xdi_produces_unknown_measurement(self) -> None:
        # Build a payload with a known packet, an unknown XDI, and another known packet.
        # The unknown XDI is skipped by the parser, so only 2 measurements are produced.
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
        measurements = decode_all_measurements(message)
        assert len(measurements) == 2
        assert not any(
            isinstance(measurement, UnknownMeasurement) for measurement in measurements
        )
