"""
Decoders that unpack OutputDataPacket.data bytes into typed reading dataclasses.
"""

from __future__ import annotations

import struct
from collections.abc import Callable

from .datatypes import OutputDataIdentifier
from .datatypes import OutputDataPacket
from .exceptions import InvalidReadingData
from .readings import Reading
from .readings import Acceleration
from .readings import AltitudeEllipsoid
from .readings import DeltaV
from .readings import GnssPvt
from .readings import MagneticField
from .readings import OrientationEuler
from .readings import OrientationQuaternion
from .readings import PacketCounter
from .readings import PositionLLEllipsoid
from .readings import RateOfTurn
from .readings import SampleTimeFine
from .readings import StatusWord
from .readings import VelocityNed


type ReadingDecoder = Callable[[OutputDataPacket], Reading]


def decode_reading(packet: OutputDataPacket) -> Reading:
    """
    Decode an OutputDataPacket into the appropriate typed reading dataclass.
    """
    return _DECODERS[packet.data_id](packet)


def _check_length(packet: OutputDataPacket, expected: int) -> None:
    if len(packet.data) != expected:
        raise InvalidReadingData(
            f"{packet.data_id.name} expects {expected} bytes, got {len(packet.data)}"
        )


def _decode_packet_counter(packet: OutputDataPacket) -> PacketCounter:
    _check_length(packet, 2)
    (counter,) = struct.unpack(">H", packet.data)
    return PacketCounter(counter=counter)


def _decode_sample_time_fine(packet: OutputDataPacket) -> SampleTimeFine:
    _check_length(packet, 4)
    (time,) = struct.unpack(">I", packet.data)
    return SampleTimeFine(time=time)


def _decode_orientation_quaternion(packet: OutputDataPacket) -> OrientationQuaternion:
    _check_length(packet, 16)
    w: float
    x: float
    y: float
    z: float
    w, x, y, z = struct.unpack(">ffff", packet.data)
    return OrientationQuaternion(w=w, x=x, y=y, z=z)


def _decode_orientation_euler(packet: OutputDataPacket) -> OrientationEuler:
    _check_length(packet, 12)
    roll: float
    pitch: float
    yaw: float
    roll, pitch, yaw = struct.unpack(">fff", packet.data)
    return OrientationEuler(roll=roll, pitch=pitch, yaw=yaw)


def _decode_acceleration(packet: OutputDataPacket) -> Acceleration:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return Acceleration(x=x, y=y, z=z)


def _decode_delta_v(packet: OutputDataPacket) -> DeltaV:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return DeltaV(x=x, y=y, z=z)


def _decode_rate_of_turn(packet: OutputDataPacket) -> RateOfTurn:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return RateOfTurn(x=x, y=y, z=z)


def _decode_magnetic_field(packet: OutputDataPacket) -> MagneticField:
    _check_length(packet, 12)
    x: float
    y: float
    z: float
    x, y, z = struct.unpack(">fff", packet.data)
    return MagneticField(x=x, y=y, z=z)


def _decode_velocity_ned(packet: OutputDataPacket) -> VelocityNed:
    _check_length(packet, 12)
    north: float
    east: float
    down: float
    north, east, down = struct.unpack(">fff", packet.data)
    return VelocityNed(north=north, east=east, down=down)


def _decode_altitude_ellipsoid(packet: OutputDataPacket) -> AltitudeEllipsoid:
    _check_length(packet, 4)
    (altitude,) = struct.unpack(">f", packet.data)
    return AltitudeEllipsoid(altitude=altitude)


def _decode_position_ll_ellipsoid(packet: OutputDataPacket) -> PositionLLEllipsoid:
    _check_length(packet, 8)
    latitude: float
    longitude: float
    latitude, longitude = struct.unpack(">ff", packet.data)
    return PositionLLEllipsoid(latitude=latitude, longitude=longitude)


def _decode_status_word(packet: OutputDataPacket) -> StatusWord:
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


def _decode_gnss_pvt(packet: OutputDataPacket) -> GnssPvt:
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


_DECODERS: dict[OutputDataIdentifier, ReadingDecoder] = {
    OutputDataIdentifier.PACKET_COUNTER: _decode_packet_counter,
    OutputDataIdentifier.SAMPLE_TIME_FINE: _decode_sample_time_fine,
    OutputDataIdentifier.ORIENTATION_QUATERNION: _decode_orientation_quaternion,
    OutputDataIdentifier.ORIENTATION_EULER: _decode_orientation_euler,
    OutputDataIdentifier.ACCELERATION: _decode_acceleration,
    OutputDataIdentifier.DELTA_V: _decode_delta_v,
    OutputDataIdentifier.RATE_OF_TURN: _decode_rate_of_turn,
    OutputDataIdentifier.MAGNETIC_FIELD: _decode_magnetic_field,
    OutputDataIdentifier.VELOCITY_NED: _decode_velocity_ned,
    OutputDataIdentifier.ALTITUDE_ELLIPSOID: _decode_altitude_ellipsoid,
    OutputDataIdentifier.POSITION_LL_ELLIPSOID: _decode_position_ll_ellipsoid,
    OutputDataIdentifier.STATUS_WORD: _decode_status_word,
    OutputDataIdentifier.GNSS_PVT: _decode_gnss_pvt,
}
