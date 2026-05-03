"""
Data types for the MTData2 output data protocol.
"""

from dataclasses import dataclass
from enum import IntEnum


class OutputDataIdentifier(IntEnum):
    """
    MTData2 output data identifier (XDI) for common MTi GNSS/INS outputs.
    """

    # Timing and counters
    PACKET_COUNTER = 0x1020
    SAMPLE_TIME_FINE = 0x1060

    # Orientation
    ORIENTATION_QUATERNION = 0x2010
    ORIENTATION_EULER = 0x2030

    # Inertial sensor data
    ACCELERATION = 0x4020
    RATE_OF_TURN = 0x8020
    MAGNETIC_FIELD = 0xC020
    DELTA_V = 0x4010

    # Navigation (GNSS/INS)
    VELOCITY_NED = 0xD010
    POSITION_LL_ELLIPSOID = 0x5040
    ALTITUDE_ELLIPSOID = 0x5020
    GNSS_PVT = 0x7010

    # Status
    STATUS_WORD = 0xE020


@dataclass(frozen=True)
class OutputDataPacket:
    """
    One output data packet contained in an MTData2 payload.
    """

    data_id: OutputDataIdentifier
    length: int  # 0–255, from the Length byte
    data: bytes  # raw payload slice of that item
