"""
Public API for the MTData2 parsing package.
"""

from .decode import (
    decode_mtdata2_packets_from_message as decode_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_message as iter_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_payload as iter_mtdata2_packets_from_payload,
)
from .datatypes import (
    MtData2PacketID as MtData2PacketID,
    MtData2Packet as MtData2Packet,
)
from xsensmti.exceptions import UnexpectedXbusMessage as UnexpectedXbusMessage
from .exceptions import (
    InvalidReadingData as InvalidReadingData,
    TruncatedPacket as TruncatedPacket,
)
from .reading_decode import (
    ReadingDecoder as ReadingDecoder,
    decode_all_readings as decode_all_readings,
    decode_reading as decode_reading,
)
from .readings import (
    Acceleration as Acceleration,
    AltitudeEllipsoid as AltitudeEllipsoid,
    BaroPressure as BaroPressure,
    DeltaQ as DeltaQ,
    DeltaV as DeltaV,
    FreeAcceleration as FreeAcceleration,
    GnssPvt as GnssPvt,
    MagneticField as MagneticField,
    OrientationEuler as OrientationEuler,
    OrientationQuaternion as OrientationQuaternion,
    PacketCounter as PacketCounter,
    PositionEcef as PositionEcef,
    PositionLLEllipsoid as PositionLLEllipsoid,
    RateOfTurn as RateOfTurn,
    Reading as Reading,
    SampleTimeFine as SampleTimeFine,
    StatusByte as StatusByte,
    StatusWord as StatusWord,
    Temperature as Temperature,
    UnknownReading as UnknownReading,
    UtcTime as UtcTime,
    VelocityNed as VelocityNed,
)

__all__ = []
