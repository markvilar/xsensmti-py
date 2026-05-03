"""
Public API for the MTData2 parsing package.
"""

from .decode import (
    decode_mtdata2_packets_from_message as decode_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_message as iter_mtdata2_packets_from_message,
    iter_mtdata2_packets_from_payload as iter_mtdata2_packets_from_payload,
)

from .datatypes import OutputDataIdentifier as OutputDataIdentifier
from .datatypes import OutputDataPacket as OutputDataPacket

from .exceptions import InvalidReadingData as InvalidReadingData
from .exceptions import NotMTData2Message as NotMTData2Message
from .exceptions import TruncatedPacket as TruncatedPacket

from .reading_decode import decode_reading as decode_reading
from .reading_decode import ReadingDecoder as ReadingDecoder

from .readings import Acceleration as Acceleration
from .readings import AltitudeEllipsoid as AltitudeEllipsoid
from .readings import DeltaV as DeltaV
from .readings import GnssPvt as GnssPvt
from .readings import MagneticField as MagneticField
from .readings import OrientationEuler as OrientationEuler
from .readings import OrientationQuaternion as OrientationQuaternion
from .readings import PacketCounter as PacketCounter
from .readings import PositionLLEllipsoid as PositionLLEllipsoid
from .readings import RateOfTurn as RateOfTurn
from .readings import SampleTimeFine as SampleTimeFine
from .readings import StatusWord as StatusWord
from .readings import VelocityNed as VelocityNed
from .readings import Reading as Reading

__all__ = []
