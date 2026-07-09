"""
Concrete Sample aliases, one per MTData2 measurement type.

These are plain assignments rather than `type` statement aliases on purpose:
they are used as runtime dispatch tokens in `set_on_sample`, where mypy must
infer the measurement type from the value. A `type` statement produces a
`TypeAliasType` that mypy rejects in that position, so the plain-assignment
`_GenericAlias` form is required.
"""

from __future__ import annotations

from xsensmti.mtdata2 import (
    Acceleration,
    AltitudeEllipsoid,
    BaroPressure,
    DeltaQ,
    DeltaV,
    FreeAcceleration,
    GnssPvt,
    MagneticField,
    Measurement,
    OrientationEuler,
    OrientationQuaternion,
    PacketCounter,
    PositionEcef,
    PositionLLEllipsoid,
    RateOfTurn,
    SampleTimeFine,
    StatusByte,
    StatusWord,
    Temperature,
    UnknownMeasurement,
    UtcTime,
    VelocityNed,
)

from .datatypes import Sample

AnySample = Sample[Measurement]

TemperatureSample = Sample[Temperature]
UtcTimeSample = Sample[UtcTime]
PacketCounterSample = Sample[PacketCounter]
SampleTimeFineSample = Sample[SampleTimeFine]
BaroPressureSample = Sample[BaroPressure]
OrientationQuaternionSample = Sample[OrientationQuaternion]
OrientationEulerSample = Sample[OrientationEuler]
AccelerationSample = Sample[Acceleration]
FreeAccelerationSample = Sample[FreeAcceleration]
DeltaVSample = Sample[DeltaV]
RateOfTurnSample = Sample[RateOfTurn]
DeltaQSample = Sample[DeltaQ]
MagneticFieldSample = Sample[MagneticField]
PositionEcefSample = Sample[PositionEcef]
VelocityNedSample = Sample[VelocityNed]
AltitudeEllipsoidSample = Sample[AltitudeEllipsoid]
PositionLLEllipsoidSample = Sample[PositionLLEllipsoid]
GnssPvtSample = Sample[GnssPvt]
StatusByteSample = Sample[StatusByte]
StatusWordSample = Sample[StatusWord]
UnknownMeasurementSample = Sample[UnknownMeasurement]
