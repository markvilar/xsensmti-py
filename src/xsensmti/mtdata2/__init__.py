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
    InvalidMeasurementData as InvalidMeasurementData,
    TruncatedPacket as TruncatedPacket,
)
from .measurement_decode import (
    MeasurementDecoder as MeasurementDecoder,
    decode_all_measurements as decode_all_measurements,
    decode_measurement as decode_measurement,
)
from .measurement_types import (
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
    Measurement as Measurement,
    SampleTimeFine as SampleTimeFine,
    StatusByte as StatusByte,
    StatusByteFlags as StatusByteFlags,
    StatusWord as StatusWord,
    StatusWordFlags as StatusWordFlags,
    Temperature as Temperature,
    UnknownMeasurement as UnknownMeasurement,
    UtcTime as UtcTime,
    VelocityNed as VelocityNed,
)

__all__: list[str] = [
    "decode_mtdata2_packets_from_message",
    "iter_mtdata2_packets_from_message",
    "iter_mtdata2_packets_from_payload",
    "MtData2PacketID",
    "MtData2Packet",
    "InvalidMeasurementData",
    "TruncatedPacket",
    "MeasurementDecoder",
    "decode_all_measurements",
    "decode_measurement",
    "Acceleration",
    "AltitudeEllipsoid",
    "BaroPressure",
    "DeltaQ",
    "DeltaV",
    "FreeAcceleration",
    "GnssPvt",
    "MagneticField",
    "OrientationEuler",
    "OrientationQuaternion",
    "PacketCounter",
    "PositionEcef",
    "PositionLLEllipsoid",
    "RateOfTurn",
    "Measurement",
    "SampleTimeFine",
    "StatusByte",
    "StatusByteFlags",
    "StatusWord",
    "StatusWordFlags",
    "Temperature",
    "UnknownMeasurement",
    "UtcTime",
    "VelocityNed",
]
