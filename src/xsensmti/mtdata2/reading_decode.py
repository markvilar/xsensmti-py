"""
Decoders that unpack MtData2Packet.data bytes into typed reading dataclasses.
"""

from __future__ import annotations

import struct

from collections.abc import Callable

from xsensmti.xbus import XbusMessage

from .datatypes import (
    MtData2PacketID,
    MtData2Packet,
)
from .decode import iter_mtdata2_packets_from_message
from .exceptions import InvalidReadingData
from .readings import (
    Acceleration,
    AltitudeEllipsoid,
    BaroPressure,
    DeltaQ,
    DeltaV,
    FreeAcceleration,
    GnssPvt,
    MagneticField,
    OrientationEuler,
    OrientationQuaternion,
    PacketCounter,
    PositionEcef,
    PositionLLEllipsoid,
    RateOfTurn,
    Reading,
    SampleTimeFine,
    StatusByte,
    StatusWord,
    Temperature,
    UnknownReading,
    UtcTime,
    VelocityNed,
)


type ReadingDecoder = Callable[[MtData2Packet], Reading]


def decode_reading(packet: MtData2Packet) -> Reading:
    """
    Decode an MtData2Packet into the appropriate typed reading dataclass.

    Returns an UnknownReading for any XDI that has no registered decoder.
    """
    decoder = _DECODERS.get(packet.data_id)
    if decoder is None:
        return UnknownReading(data_id=int(packet.data_id), data=packet.data)
    return decoder(packet)


def decode_all_readings(message: XbusMessage) -> list[Reading]:
    """
    Decode all readings from an MTDATA2 XbusMessage.

    Arguments
    ---------
    message: An XbusMessage with MID MTDATA2.

    Returns
    -------
    A list of typed reading dataclasses, one per MTData2 packet in the payload.
    """
    return [
        decode_reading(packet) for packet in iter_mtdata2_packets_from_message(message)
    ]


def _check_length(packet: MtData2Packet, expected: int) -> None:
    if len(packet.data) != expected:
        raise InvalidReadingData(
            f"{packet.data_id.name} expects {expected} bytes, got {len(packet.data)}"
        )


def _decode_packet_counter(packet: MtData2Packet) -> PacketCounter:
    _check_length(packet, 2)
    (counter,) = struct.unpack(">H", packet.data)
    return PacketCounter(counter=counter)


def _decode_sample_time_fine(packet: MtData2Packet) -> SampleTimeFine:
    _check_length(packet, 4)
    (time,) = struct.unpack(">I", packet.data)
    return SampleTimeFine(time=time)


def _decode_orientation_quaternion(packet: MtData2Packet) -> OrientationQuaternion:
    _check_length(packet, 16)
    w: float
    x: float
    y: float
    z: float
    w, x, y, z = struct.unpack(">ffff", packet.data)
    return OrientationQuaternion(w=w, x=x, y=y, z=z)


def _decode_orientation_euler(packet: MtData2Packet) -> OrientationEuler:
    _check_length(packet, 12)
    roll: float
    pitch: float
    yaw: float
    roll, pitch, yaw = struct.unpack(">fff", packet.data)
    return OrientationEuler(roll=roll, pitch=pitch, yaw=yaw)


def _decode_acceleration(packet: MtData2Packet) -> Acceleration:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return Acceleration(x=x, y=y, z=z)


def _decode_delta_v(packet: MtData2Packet) -> DeltaV:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return DeltaV(x=x, y=y, z=z)


def _decode_rate_of_turn(packet: MtData2Packet) -> RateOfTurn:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return RateOfTurn(x=x, y=y, z=z)


def _decode_magnetic_field(packet: MtData2Packet) -> MagneticField:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return MagneticField(x=x, y=y, z=z)


def _decode_velocity_ned(packet: MtData2Packet) -> VelocityNed:
    _check_length(packet, 12)
    north: float
    east: float
    down: float
    north, east, down = struct.unpack(">fff", packet.data)
    return VelocityNed(north=north, east=east, down=down)


def _decode_altitude_ellipsoid(packet: MtData2Packet) -> AltitudeEllipsoid:
    _check_length(packet, 4)
    (altitude,) = struct.unpack(">f", packet.data)
    return AltitudeEllipsoid(altitude=altitude)


def _decode_position_ll_ellipsoid(packet: MtData2Packet) -> PositionLLEllipsoid:
    _check_length(packet, 8)
    latitude: float
    longitude: float
    latitude, longitude = struct.unpack(">ff", packet.data)
    return PositionLLEllipsoid(latitude=latitude, longitude=longitude)


def _decode_status_word(packet: MtData2Packet) -> StatusWord:
    _check_length(packet, 4)
    (status,) = struct.unpack(">I", packet.data)
    return StatusWord(status=status)


# UBX-NAV-PVT layout (92 bytes, big-endian):
#   I  itow        uint32  GPS time of week (ms)
#   H  year        uint16
#   B  month       uint8
#   B  day         uint8
#   B  hour        uint8
#   B  minute      uint8
#   B  second      uint8
#   B  valid       uint8   validity flags
#   I  t_acc       uint32  time accuracy (ns)
#   i  nano        int32   sub-second fraction (ns)
#   B  fix_type    uint8
#   B  flags       uint8
#   B  flags2      uint8
#   B  num_sv      uint8
#   i  lon         int32   × 1e-7 → degrees
#   i  lat         int32   × 1e-7 → degrees
#   i  height      int32   × 1e-3 → metres (above ellipsoid)
#   i  h_msl       int32   × 1e-3 → metres (above MSL)
#   I  h_acc       uint32  × 1e-3 → metres
#   I  v_acc       uint32  × 1e-3 → metres
#   i  vel_n       int32   × 1e-3 → m/s
#   i  vel_e       int32   × 1e-3 → m/s
#   i  vel_d       int32   × 1e-3 → m/s
#   i  g_speed     int32   × 1e-3 → m/s
#   i  head_mot    int32   × 1e-5 → degrees
#   I  s_acc       uint32  × 1e-3 → m/s
#   I  head_acc    uint32  × 1e-5 → degrees
#   H  p_dop       uint16  × 0.01
#   H  reserved1   uint16  (discarded)
#   I  reserved2   uint32  (discarded)
#   i  head_veh    int32   × 1e-5 → degrees
#   h  mag_dec     int16   × 0.01 → degrees
#   H  mag_acc     uint16  × 0.01 → degrees
_GNSS_PVT_FORMAT: str = ">IHBBBBBBIiBBBBiiiiIIiiiiIIHHIihH"
_GNSS_PVT_SIZE: int = struct.calcsize(_GNSS_PVT_FORMAT)


def _decode_gnss_pvt(packet: MtData2Packet) -> GnssPvt:
    _check_length(packet, _GNSS_PVT_SIZE)
    (
        itow,
        year,
        month,
        day,
        hour,
        minute,
        second,
        valid,
        t_acc,
        nano,
        fix_type,
        flags,
        flags2,
        num_sv,
        lon,
        lat,
        height,
        h_msl,
        h_acc,
        v_acc,
        vel_n,
        vel_e,
        vel_d,
        g_speed,
        head_mot,
        s_acc,
        head_acc,
        p_dop,
        _reserved1,
        _reserved2,
        head_veh,
        mag_dec,
        mag_acc,
    ) = struct.unpack(_GNSS_PVT_FORMAT, packet.data)
    return GnssPvt(
        itow=itow,
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        valid=valid,
        time_accuracy=t_acc,
        nanoseconds=nano,
        fix_type=fix_type,
        flags=flags,
        flags2=flags2,
        num_sv=num_sv,
        longitude=lon * 1e-7,
        latitude=lat * 1e-7,
        height=height * 1e-3,
        height_msl=h_msl * 1e-3,
        h_accuracy=h_acc * 1e-3,
        v_accuracy=v_acc * 1e-3,
        vel_north=vel_n * 1e-3,
        vel_east=vel_e * 1e-3,
        vel_down=vel_d * 1e-3,
        ground_speed=g_speed * 1e-3,
        heading_motion=head_mot * 1e-5,
        speed_accuracy=s_acc * 1e-3,
        heading_accuracy=head_acc * 1e-5,
        position_dop=p_dop * 0.01,
        heading_vehicle=head_veh * 1e-5,
        mag_declination=mag_dec * 0.01,
        mag_accuracy=mag_acc * 0.01,
    )


def _decode_temperature(packet: MtData2Packet) -> Temperature:
    _check_length(packet, 4)
    (temperature,) = struct.unpack(">f", packet.data)
    return Temperature(temperature=temperature)


def _decode_utc_time(packet: MtData2Packet) -> UtcTime:
    _check_length(packet, 12)
    nanoseconds: int
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    valid: int
    nanoseconds, year, month, day, hour, minute, second, valid = struct.unpack(
        ">IHBBBBBB", packet.data
    )
    return UtcTime(
        nanoseconds=nanoseconds,
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        valid=valid,
    )


def _decode_baro_pressure(packet: MtData2Packet) -> BaroPressure:
    _check_length(packet, 4)
    (pressure,) = struct.unpack(">I", packet.data)
    return BaroPressure(pressure=pressure)


def _decode_free_acceleration(packet: MtData2Packet) -> FreeAcceleration:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return FreeAcceleration(x=x, y=y, z=z)


def _decode_position_ecef(packet: MtData2Packet) -> PositionEcef:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return PositionEcef(x=x, y=y, z=z)


def _decode_delta_q(packet: MtData2Packet) -> DeltaQ:
    _check_length(packet, 16)
    w: float
    x: float
    y: float
    z: float
    w, x, y, z = struct.unpack(">ffff", packet.data)
    return DeltaQ(w=w, x=x, y=y, z=z)


def _decode_status_byte(packet: MtData2Packet) -> StatusByte:
    _check_length(packet, 1)
    (status,) = struct.unpack(">B", packet.data)
    return StatusByte(status=status)


_DECODERS: dict[MtData2PacketID, ReadingDecoder] = {
    MtData2PacketID.TEMPERATURE: _decode_temperature,
    MtData2PacketID.UTC_TIME: _decode_utc_time,
    MtData2PacketID.PACKET_COUNTER: _decode_packet_counter,
    MtData2PacketID.SAMPLE_TIME_FINE: _decode_sample_time_fine,
    MtData2PacketID.BARO_PRESSURE: _decode_baro_pressure,
    MtData2PacketID.ORIENTATION_QUATERNION: _decode_orientation_quaternion,
    MtData2PacketID.ORIENTATION_EULER: _decode_orientation_euler,
    MtData2PacketID.ACCELERATION: _decode_acceleration,
    MtData2PacketID.FREE_ACCELERATION: _decode_free_acceleration,
    MtData2PacketID.DELTA_V: _decode_delta_v,
    MtData2PacketID.RATE_OF_TURN: _decode_rate_of_turn,
    MtData2PacketID.DELTA_Q: _decode_delta_q,
    MtData2PacketID.MAGNETIC_FIELD: _decode_magnetic_field,
    MtData2PacketID.POSITION_ECEF: _decode_position_ecef,
    MtData2PacketID.VELOCITY_NED: _decode_velocity_ned,
    MtData2PacketID.ALTITUDE_ELLIPSOID: _decode_altitude_ellipsoid,
    MtData2PacketID.POSITION_LL_ELLIPSOID: _decode_position_ll_ellipsoid,
    MtData2PacketID.GNSS_PVT: _decode_gnss_pvt,
    MtData2PacketID.STATUS_BYTE: _decode_status_byte,
    MtData2PacketID.STATUS_WORD: _decode_status_word,
}
