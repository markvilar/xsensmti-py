"""
Output configuration presets for common MTi device types.
"""

from __future__ import annotations

import struct

from xsensmti.mtdata2 import MtData2PacketID

type XdiRatePair = tuple[MtData2PacketID, int]
type OutputPreset = tuple[XdiRatePair, ...]

PRESET_NAMES: tuple[str, ...] = ("imu", "vru", "gnss")

VALID_RATES: frozenset[int] = frozenset({1, 2, 4, 5, 10, 20, 25, 50, 100, 200, 400})

_GNSS_PVT_MAX_RATE: int = 4

_IMU_BASE: tuple[MtData2PacketID, ...] = (
    MtData2PacketID.PACKET_COUNTER,
    MtData2PacketID.SAMPLE_TIME_FINE,
    MtData2PacketID.ACCELERATION,
    MtData2PacketID.RATE_OF_TURN,
    MtData2PacketID.MAGNETIC_FIELD,
    MtData2PacketID.STATUS_WORD,
)

_VRU_BASE: tuple[MtData2PacketID, ...] = (
    MtData2PacketID.PACKET_COUNTER,
    MtData2PacketID.SAMPLE_TIME_FINE,
    MtData2PacketID.ORIENTATION_QUATERNION,
    MtData2PacketID.ACCELERATION,
    MtData2PacketID.RATE_OF_TURN,
    MtData2PacketID.MAGNETIC_FIELD,
    MtData2PacketID.STATUS_WORD,
)

_GNSS_BASE: tuple[MtData2PacketID, ...] = (
    MtData2PacketID.PACKET_COUNTER,
    MtData2PacketID.SAMPLE_TIME_FINE,
    MtData2PacketID.ORIENTATION_QUATERNION,
    MtData2PacketID.ACCELERATION,
    MtData2PacketID.RATE_OF_TURN,
    MtData2PacketID.VELOCITY_NED,
    MtData2PacketID.POSITION_LL_ELLIPSOID,
    MtData2PacketID.ALTITUDE_ELLIPSOID,
    MtData2PacketID.GNSS_PVT,
    MtData2PacketID.STATUS_WORD,
)


def get_preset(name: str, rate: int = 100) -> OutputPreset:
    """
    Return XDI/rate pairs for the named preset at the given output rate.

    GNSS_PVT is always capped at 4 Hz regardless of `rate`.
    Raises ValueError for unknown preset names or invalid rates.
    """
    if rate not in VALID_RATES:
        raise ValueError(
            f"rate {rate} Hz is not supported; valid rates: {sorted(VALID_RATES)}"
        )

    xdis: tuple[MtData2PacketID, ...]
    match name:
        case "imu":
            xdis = _IMU_BASE
        case "vru":
            xdis = _VRU_BASE
        case "gnss":
            xdis = _GNSS_BASE
        case _:
            raise ValueError(f"unknown preset {name!r}; valid presets: {PRESET_NAMES}")

    return tuple(
        (
            xdi,
            min(rate, _GNSS_PVT_MAX_RATE) if xdi == MtData2PacketID.GNSS_PVT else rate,
        )
        for xdi in xdis
    )


def build_output_configuration_payload(preset: OutputPreset) -> bytes:
    """
    Encode an OutputPreset into the SetOutputConfiguration payload.

    Each XDI/rate pair becomes 4 bytes: [XDI_HI, XDI_LO, RATE_HI, RATE_LO].
    """
    return b"".join(struct.pack(">HH", int(xdi), rate) for xdi, rate in preset)
