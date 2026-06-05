"""
Typed dataclasses for decoded MTData2 sensor readings.

Each type corresponds to one MtData2PacketID and holds physically
meaningful values (degrees, metres, m/s, rad/s) rather than raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag


@dataclass(frozen=True)
class Temperature:
    """Temperature in degrees Celsius (XDI 0x0810)."""

    temperature: float


@dataclass(frozen=True)
class UtcTime:
    """UTC timestamp (XDI 0x1010)."""

    nanoseconds: int
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    valid: int  # validity flags bitmask


@dataclass(frozen=True)
class PacketCounter:
    """Packet sequence counter (XDI 0x1020)."""

    counter: int


@dataclass(frozen=True)
class SampleTimeFine:
    """Sample timestamp in 10 kHz clock ticks (XDI 0x1060)."""

    time: int


@dataclass(frozen=True)
class BaroPressure:
    """Barometric pressure in Pascal (XDI 0x3010)."""

    pressure: int


@dataclass(frozen=True)
class OrientationQuaternion:
    """Orientation as a unit quaternion (XDI 0x2010)."""

    w: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class OrientationEuler:
    """Orientation as Euler angles in degrees (XDI 0x2030)."""

    roll: float
    pitch: float
    yaw: float


@dataclass(frozen=True)
class Acceleration:
    """Calibrated acceleration in m/s² (XDI 0x4020)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class DeltaV:
    """Integrated delta-velocity in m/s (XDI 0x4010)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class FreeAcceleration:
    """Gravity-compensated free acceleration in m/s² (XDI 0x4030)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class RateOfTurn:
    """Calibrated rate of turn in rad/s (XDI 0x8020)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class MagneticField:
    """Calibrated magnetic field in arbitrary units (XDI 0xC020)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class DeltaQ:
    """Delta quaternion orientation increment (XDI 0x8030)."""

    w: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class PositionEcef:
    """Position in ECEF coordinates in metres (XDI 0x5030)."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class VelocityNed:
    """Velocity in the NED frame in m/s (XDI 0xD010)."""

    north: float
    east: float
    down: float


@dataclass(frozen=True)
class AltitudeEllipsoid:
    """Altitude above the WGS-84 ellipsoid in metres (XDI 0x5020)."""

    altitude: float


@dataclass(frozen=True)
class PositionLLEllipsoid:
    """Geodetic latitude and longitude on the WGS-84 ellipsoid in degrees (XDI 0x5040)."""

    latitude: float
    longitude: float


class StatusByteFlags(IntFlag):
    """Bitmask flags for StatusByte (XDI 0xE010). The lower byte of StatusWordFlags."""

    SELFTEST = 0x01
    FILTER_VALID = 0x02
    GNSS_FIX = 0x04
    NO_ROTATION_UPDATE_STATUS_0 = 0x08
    NO_ROTATION_UPDATE_STATUS_1 = 0x10
    REPRESENTATIVE_MOTION = 0x20
    CLOCK_BIAS_ESTIMATION = 0x40


class StatusWordFlags(IntFlag):
    """Bitmask flags for StatusWord (XDI 0xE020). Lower byte matches StatusByteFlags."""

    SELFTEST = 0x00000001
    FILTER_VALID = 0x00000002
    GNSS_FIX = 0x00000004
    NO_ROTATION_UPDATE_STATUS_0 = 0x00000008
    NO_ROTATION_UPDATE_STATUS_1 = 0x00000010
    REPRESENTATIVE_MOTION = 0x00000020
    CLOCK_BIAS_ESTIMATION = 0x00000040
    CLIP_ACC_X = 0x00000100
    CLIP_ACC_Y = 0x00000200
    CLIP_ACC_Z = 0x00000400
    CLIP_GYR_X = 0x00000800
    CLIP_GYR_Y = 0x00001000
    CLIP_GYR_Z = 0x00002000
    CLIP_MAG_X = 0x00004000
    CLIP_MAG_Y = 0x00008000
    CLIP_MAG_Z = 0x00010000
    GNSS_PVT_STATUS_0 = 0x00020000
    GNSS_PVT_STATUS_1 = 0x00040000
    GNSS_PVT_LATENCY_0 = 0x00080000
    GNSS_PVT_LATENCY_1 = 0x00100000
    GNSS_PVT_DOP_0 = 0x00200000
    GNSS_PVT_DOP_1 = 0x00400000
    ICC_COMMAND_RECEIVED = 0x00800000
    ICC_IN_PROGRESS = 0x01000000
    ICC_GRACE_PERIOD = 0x02000000


@dataclass(frozen=True)
class StatusByte:
    """Compact device status flags (XDI 0xE010). The lower byte of StatusWord."""

    status: StatusByteFlags


@dataclass(frozen=True)
class StatusWord:
    """Device status flags (XDI 0xE020)."""

    status: StatusWordFlags


@dataclass(frozen=True)
class GnssPvt:
    """
    GNSS position/velocity/time solution (XDI 0x7010).

    Parsed from the XSens GnssPvtData format (Table 25, MT Low Level
    Communication Protocol Documentation). Positional and velocity fields are
    stored in physical units (degrees, metres, m/s).
    """

    itow: int  # GPS time of week (ms)
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    valid: int  # validity flags bitmask
    time_accuracy: int  # time accuracy estimate (ns)
    nanoseconds: int  # sub-second fraction (ns, signed)
    fix_type: int  # 0=no fix, 1=dead rec., 2=2-D, 3=3-D, 4=GNSS+dead rec., 5=time only
    flags: int  # fix status flags bitmask
    num_sv: int  # number of satellites used in solution
    longitude: float  # degrees
    latitude: float  # degrees
    height: float  # height above ellipsoid (m)
    height_msl: float  # height above mean sea level (m)
    h_accuracy: float  # horizontal accuracy estimate (m)
    v_accuracy: float  # vertical accuracy estimate (m)
    vel_north: float  # NED north velocity (m/s)
    vel_east: float  # NED east velocity (m/s)
    vel_down: float  # NED down velocity (m/s)
    ground_speed: float  # 2-D ground speed (m/s)
    heading_motion: float  # 2-D heading of motion (deg)
    speed_accuracy: float  # speed accuracy estimate (m/s)
    heading_accuracy: float  # heading accuracy estimate (deg)
    heading_vehicle: float  # 2-D heading of vehicle (deg)
    geom_dop: float  # geometric dilution of precision
    pos_dop: float  # position dilution of precision
    time_dop: float  # time dilution of precision
    vert_dop: float  # vertical dilution of precision
    horiz_dop: float  # horizontal dilution of precision
    north_dop: float  # northing dilution of precision
    east_dop: float  # easting dilution of precision


@dataclass(frozen=True)
class UnknownReading:
    """Raw bytes for an MTData2 packet whose XDI has no registered decoder."""

    data_id: int
    data: bytes


type Reading = (
    Temperature
    | UtcTime
    | PacketCounter
    | SampleTimeFine
    | BaroPressure
    | OrientationQuaternion
    | OrientationEuler
    | Acceleration
    | FreeAcceleration
    | DeltaV
    | RateOfTurn
    | DeltaQ
    | MagneticField
    | PositionEcef
    | VelocityNed
    | AltitudeEllipsoid
    | PositionLLEllipsoid
    | GnssPvt
    | StatusByte
    | StatusWord
    | UnknownReading
)
