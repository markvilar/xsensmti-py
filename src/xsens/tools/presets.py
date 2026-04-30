"""
Output configuration presets for common MTi device types.
"""

from __future__ import annotations

import struct

from xsens.mtdata2.datatypes import OutputDataIdentifier

type XdiRatePair = tuple[OutputDataIdentifier, int]
type OutputPreset = tuple[XdiRatePair, ...]

PRESET_NAMES: tuple[str, ...] = ("imu", "vru", "gnss")

VALID_RATES: frozenset[int] = frozenset({1, 2, 4, 5, 10, 20, 25, 50, 100, 200, 400})

_GNSS_PVT_MAX_RATE: int = 4

_IMU_BASE: tuple[OutputDataIdentifier, ...] = (
    OutputDataIdentifier.PACKET_COUNTER,
    OutputDataIdentifier.SAMPLE_TIME_FINE,
    OutputDataIdentifier.ACCELERATION,
    OutputDataIdentifier.RATE_OF_TURN,
    OutputDataIdentifier.MAGNETIC_FIELD,
    OutputDataIdentifier.STATUS_WORD,
)

_VRU_BASE: tuple[OutputDataIdentifier, ...] = (
    OutputDataIdentifier.PACKET_COUNTER,
    OutputDataIdentifier.SAMPLE_TIME_FINE,
    OutputDataIdentifier.ORIENTATION_QUATERNION,
    OutputDataIdentifier.ACCELERATION,
    OutputDataIdentifier.RATE_OF_TURN,
    OutputDataIdentifier.MAGNETIC_FIELD,
    OutputDataIdentifier.STATUS_WORD,
)

_GNSS_BASE: tuple[OutputDataIdentifier, ...] = (
    OutputDataIdentifier.PACKET_COUNTER,
    OutputDataIdentifier.SAMPLE_TIME_FINE,
    OutputDataIdentifier.ORIENTATION_QUATERNION,
    OutputDataIdentifier.ACCELERATION,
    OutputDataIdentifier.RATE_OF_TURN,
    OutputDataIdentifier.VELOCITY_NED,
    OutputDataIdentifier.POSITION_LL_ELLIPSOID,
    OutputDataIdentifier.ALTITUDE_ELLIPSOID,
    OutputDataIdentifier.GNSS_PVT,
    OutputDataIdentifier.STATUS_WORD,
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

    xdis: tuple[OutputDataIdentifier, ...]
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
            min(rate, _GNSS_PVT_MAX_RATE)
            if xdi == OutputDataIdentifier.GNSS_PVT
            else rate,
        )
        for xdi in xdis
    )


def build_output_configuration_payload(preset: OutputPreset) -> bytes:
    """
    Encode an OutputPreset into the SetOutputConfiguration payload.

    Each XDI/rate pair becomes 4 bytes: [XDI_HI, XDI_LO, RATE_HI, RATE_LO].
    """
    return b"".join(struct.pack(">HH", int(xdi), rate) for xdi, rate in preset)
