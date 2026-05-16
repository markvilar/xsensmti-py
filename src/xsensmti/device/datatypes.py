"""
Data types for MtiDevice state and configuration responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag

from xsensmti.mtdata2 import MtData2PacketID

type MtiDeviceOutputConfig = list[tuple[MtData2PacketID, int]]


class MtiDeviceState(IntEnum):
    CONFIG = 0
    MEASUREMENT = 1


class MtiDeviceOptionFlags(IntFlag):
    DISABLE_AUTO_STORE = 0x00000001
    DISABLE_AUTO_MEASUREMENT = 0x00000002
    ENABLE_BEIDOU = 0x00000004
    ENABLE_AHS = 0x00000010
    ENABLE_ORIENTATION_SMOOTHER = 0x00000020
    ENABLE_CONFIGURABLE_BUS_ID = 0x00000040
    ENABLE_IN_RUN_COMPASS_CALIBRATION = 0x00000080
    ENABLE_CONFIG_MESSAGE_AT_STARTUP = 0x00000200
    ENABLE_COLD_FILTER_RESETS = 0x00000400
    ENABLE_POSITION_VELOCITY_SMOOTHER = 0x00000800
    ENABLE_CONTINUOUS_ZRU = 0x00001000


_Flags = MtiDeviceOptionFlags


@dataclass(frozen=True)
class MtiDeviceOptions:
    """
    Device option flags parsed from the OPTION_FLAGS_ACK payload.

    Each field corresponds to one bit in the 32-bit option flags bitmask.
    Not all flags are supported by every device variant.
    """

    disable_auto_store: bool
    disable_auto_measurement: bool
    enable_beidou: bool
    enable_ahs: bool
    enable_orientation_smoother: bool
    enable_configurable_bus_id: bool
    enable_in_run_compass_calibration: bool
    enable_config_message_at_startup: bool
    enable_cold_filter_resets: bool
    enable_position_velocity_smoother: bool
    enable_continuous_zru: bool

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceOptions:
        flags = MtiDeviceOptionFlags(int.from_bytes(payload, "big"))
        return cls(
            disable_auto_store=_Flags.DISABLE_AUTO_STORE in flags,
            disable_auto_measurement=_Flags.DISABLE_AUTO_MEASUREMENT in flags,
            enable_beidou=_Flags.ENABLE_BEIDOU in flags,
            enable_ahs=_Flags.ENABLE_AHS in flags,
            enable_orientation_smoother=_Flags.ENABLE_ORIENTATION_SMOOTHER in flags,
            enable_configurable_bus_id=_Flags.ENABLE_CONFIGURABLE_BUS_ID in flags,
            enable_in_run_compass_calibration=_Flags.ENABLE_IN_RUN_COMPASS_CALIBRATION
            in flags,
            enable_config_message_at_startup=_Flags.ENABLE_CONFIG_MESSAGE_AT_STARTUP
            in flags,
            enable_cold_filter_resets=_Flags.ENABLE_COLD_FILTER_RESETS in flags,
            enable_position_velocity_smoother=_Flags.ENABLE_POSITION_VELOCITY_SMOOTHER
            in flags,
            enable_continuous_zru=_Flags.ENABLE_CONTINUOUS_ZRU in flags,
        )


@dataclass(frozen=True)
class MtiDeviceFilterProfile:
    """
    Active filter profile parsed from the FILTER_PROFILE_ACK payload.

    MTi 600-series devices use the modern method: the payload is an ASCII
    label string (1–62 bytes), e.g. "Robust" or "Robust/VRU" for a
    base-profile/heading-behaviour combination.

    Older devices (MTi 1/7/10/100/710) use the classic method: the payload
    is 2 bytes — version (byte 0) and a numeric profile index (byte 1).
    """

    label: str
    version: int
    index: int

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceFilterProfile:
        if len(payload) == 2:
            return cls(label="", version=payload[0], index=payload[1])
        return cls(
            label=payload.decode("ascii").rstrip(),
            version=0,
            index=0,
        )


@dataclass(frozen=True)
class MtiDeviceConfig:
    """
    Device configuration parsed from the CONFIGURATION payload (118 bytes).

    MTi-600 series devices use an extended layout with an 8-byte device ID
    (first 4 bytes are always zero). These devices expose sampling_period,
    output_skip_factor, output_mode, and output_settings as None because
    output configuration is managed entirely via SetOutputConfiguration.

    Older series devices (MTi 1/7/10/100/710) expose all four fields.
    """

    num_devices: int
    sampling_period: int | None
    output_skip_factor: int | None
    output_mode: int | None
    output_settings: int | None

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceConfig:
        num_devices: int = int.from_bytes(payload[96:98], "big")

        if payload[0:4] == b"\x00\x00\x00\x00":
            return cls(
                num_devices=num_devices,
                sampling_period=None,
                output_skip_factor=None,
                output_mode=None,
                output_settings=None,
            )

        return cls(
            num_devices=num_devices,
            sampling_period=int.from_bytes(payload[4:6], "big"),
            output_skip_factor=int.from_bytes(payload[6:8], "big"),
            output_mode=int.from_bytes(payload[104:106], "big"),
            output_settings=int.from_bytes(payload[106:110], "big"),
        )
