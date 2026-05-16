"""
Typed dataclasses for decoded MTData2 sensor readings.

Each type corresponds to one MtData2PacketID and holds physically
meaningful values (degrees, metres, m/s, rad/s) rather than raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class StatusByte:
    """Compact device status flags (XDI 0xE010)."""

    status: int


@dataclass(frozen=True)
class StatusWord:
    """Device status flags (XDI 0xE020)."""

    status: int


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
