"""
Data types for the MTData2 output data protocol.
"""

from dataclasses import dataclass
from enum import IntEnum


class MtData2PacketID(IntEnum):
    """
    MTData2 output data identifier (XDI) for common MTi GNSS/INS outputs.
    """

    # Environmental
    TEMPERATURE = 0x0810

    # Timing
    UTC_TIME = 0x1010
    PACKET_COUNTER = 0x1020
    SAMPLE_TIME_FINE = 0x1060

    # Orientation
    ORIENTATION_QUATERNION = 0x2010
    ORIENTATION_EULER = 0x2030

    # Pressure
    BARO_PRESSURE = 0x3010

    # Inertial
    DELTA_V = 0x4010
    ACCELERATION = 0x4020
    FREE_ACCELERATION = 0x4030
    RATE_OF_TURN = 0x8020
    DELTA_Q = 0x8030
    MAGNETIC_FIELD = 0xC020

    # Navigation (GNSS/INS)
    ALTITUDE_ELLIPSOID = 0x5020
    POSITION_ECEF = 0x5030
    POSITION_LL_ELLIPSOID = 0x5040
    GNSS_PVT = 0x7010
    VELOCITY_NED = 0xD010

    # Status
    STATUS_BYTE = 0xE010
    STATUS_WORD = 0xE020


@dataclass(frozen=True)
class MtData2Packet:
    """
    One output data packet contained in an MTData2 payload.
    """

    data_id: MtData2PacketID
    length: int  # 0–255, from the Length byte
    data: bytes  # raw payload slice of that item
