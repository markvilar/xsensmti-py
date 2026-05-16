"""
Public API for the MTData2 parsing package.
"""

from .decode import (
    decode_mtdata2_packets_from_message as decode_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_message as iter_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_payload as iter_mtdata2_packets_from_payload,
)
from .datatypes import (
    OutputDataIdentifier as OutputDataIdentifier,
    OutputDataPacket as OutputDataPacket,
)
from .exceptions import (
    InvalidReadingData as InvalidReadingData,
    NotMTData2Message as NotMTData2Message,
    TruncatedPacket as TruncatedPacket,
)
from .reading_decode import (
    ReadingDecoder as ReadingDecoder,
    decode_reading as decode_reading,
)
from .readings import (
    Acceleration as Acceleration,
    AltitudeEllipsoid as AltitudeEllipsoid,
    DeltaV as DeltaV,
    GnssPvt as GnssPvt,
    MagneticField as MagneticField,
    OrientationEuler as OrientationEuler,
    OrientationQuaternion as OrientationQuaternion,
    PacketCounter as PacketCounter,
    PositionLLEllipsoid as PositionLLEllipsoid,
    RateOfTurn as RateOfTurn,
    Reading as Reading,
    SampleTimeFine as SampleTimeFine,
    StatusWord as StatusWord,
    VelocityNed as VelocityNed,
)

__all__ = []
