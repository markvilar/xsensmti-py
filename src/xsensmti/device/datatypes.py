"""
Data types for MtiDevice state and configuration responses.
"""

from __future__ import annotations

import re

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import IntEnum, IntFlag

from xsensmti.mtdata2 import (
    Measurement,
    MtData2PacketID,
)
from xsensmti.xbus import XbusMessage


type MtiDeviceID = int


@dataclass(frozen=True)
class MtiPortInfo:
    """Connection parameters for a single MTi device."""

    port: str
    baud: int
    vid: int | None = None
    pid: int | None = None

    @property
    def is_usb(self) -> bool:
        return self.vid is not None and self.pid is not None

    @property
    def usb_info(self) -> str | None:
        if self.vid is None or self.pid is None:
            return None
        return f"VID:PID={self.vid:04X}:{self.pid:04X}"


@dataclass(frozen=True)
class MtiDeviceInfo:
    """Identifier for a MTi device."""

    device_id: int
    product_code: str
    firmware_version: str
    hardware_version: str


@dataclass(frozen=True)
class MtiScanResult:
    """
    Result of a single serial port scan.

    Attributes:
        port_info: Connection parameters reported by the OS for this port.
    """

    port_info: MtiPortInfo


@dataclass(frozen=True)
class MtiProbeResult:
    """
    Result of probing a single serial port for an XSens MTi device.

    Attributes:
        port_info: Connection parameters used during the probe.
        device_info: Device identity queried during the probe.
    """

    port_info: MtiPortInfo
    device_info: MtiDeviceInfo


@dataclass(frozen=True)
class MtiMessageHeader:
    """Receipt metadata for a single Xbus message."""

    device_info: MtiDeviceInfo
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass(frozen=True)
class MtiMessage:
    """A received Xbus message together with its receipt metadata."""

    header: MtiMessageHeader
    xbus_message: XbusMessage


@dataclass(frozen=True)
class Sample[T: Measurement]:
    """
    A decoded measurement together with its receipt metadata.

    Attributes:
        header: Receipt metadata for the Xbus message the measurement was decoded from.
        payload: The decoded measurement.
    """

    header: MtiMessageHeader
    payload: T


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
        """
        Parse the option flags from an OPTION_FLAGS_ACK payload.

        Args:
            payload: The 4-byte option flags bitmask.
        """
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

    def to_payload(self) -> bytes:
        """
        Encode the options as an OPTION_FLAGS payload.

        The payload is 8 bytes: a 32-bit SetFlags mask followed by a 32-bit
        ClearFlags mask. The device leaves a flag untouched when its bit is zero
        in both masks, so every field is written explicitly — set bits for the
        fields that are True, clear bits for the fields that are False. This
        makes the write an absolute state, matching what from_payload() returns.
        """
        set_flags: int = 0
        clear_flags: int = 0
        for field_name, flag in _OPTION_FLAG_FIELDS:
            if getattr(self, field_name):
                set_flags |= flag
            else:
                clear_flags |= flag
        return set_flags.to_bytes(4, "big") + clear_flags.to_bytes(4, "big")


@dataclass(frozen=True)
class MtiDeviceFilterProfile:
    """
    A filter profile, as reported by the device.

    Filter profiles are predefined in device firmware; they cannot be created or
    edited, only selected. AVAILABLE_FILTER_PROFILES_ACK reports all three fields
    below for every device, so a profile is a uniform triple regardless of family.

    The FILTER_PROFILE_ACK payload is lossier and comes in two forms. MTi
    600-series devices use the modern method: an ASCII label string (1–62 bytes),
    e.g. "Robust" or "Robust/VRU" for a base-profile/heading-behaviour
    combination. Older devices (MTi 1/7/10/100/710) use the classic method:
    a 16-bit profile type and nothing else — no label, no version. Pass the
    result through resolve_filter_profile() to fill those in.

    Attributes:
        label: Profile label, empty when a classic payload has not been resolved.
        version: Profile version, zero when a classic payload has not been resolved.
        index: Numeric profile type, zero when the device reported a modern profile.
    """

    label: str
    version: int
    index: int

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceFilterProfile:
        """
        Parse a filter profile from a FILTER_PROFILE_ACK payload.

        The payload is lossy: classic devices report only the numeric type and
        modern devices only the label. Pass the result through
        resolve_filter_profile() to recover the missing fields.

        Args:
            payload: A 2-byte profile type, or an ASCII label.
        """
        if len(payload) == 2:
            return cls(label="", version=0, index=int.from_bytes(payload, "big"))
        return cls(
            label=payload.decode("ascii").rstrip(),
            version=0,
            index=0,
        )

    @classmethod
    def list_from_payload(cls, payload: bytes) -> list[MtiDeviceFilterProfile]:
        """
        Parse the AVAILABLE_FILTER_PROFILES_ACK payload.

        The payload always holds 5 slots of 22 bytes — type (1 byte), version
        (1 byte), and a 20-byte space-padded label. Devices with fewer than 5
        profiles report the remaining slots with a type of 0; those are skipped.

        Args:
            payload: Payload of an AVAILABLE_FILTER_PROFILES_ACK message.

        Returns:
            The profiles the device reports, excluding the empty slots.
        """
        profiles: list[MtiDeviceFilterProfile] = []
        for offset in range(0, len(payload), _FILTER_PROFILE_SLOT_SIZE):
            slot: bytes = payload[offset : offset + _FILTER_PROFILE_SLOT_SIZE]
            profile_type: int = slot[0]
            if profile_type == 0:
                continue
            profiles.append(
                cls(
                    label=slot[2:].decode("ascii").rstrip(),
                    version=slot[1],
                    index=profile_type,
                )
            )
        return profiles

    def to_classic_payload(self) -> bytes:
        """
        Encode as the FILTER_PROFILE payload used by pre-600-series devices.

        The payload is the 16-bit profile type. The version is not sent — it is
        a property of the profile stored on the device, not part of the selection.
        """
        return self.index.to_bytes(2, "big")

    def to_modern_payload(self) -> bytes:
        """Encode as the ASCII FILTER_PROFILE payload used by 600-series devices."""
        return self.label.encode("ascii")


def resolve_filter_profile(
    profile: MtiDeviceFilterProfile,
    available: list[MtiDeviceFilterProfile],
) -> MtiDeviceFilterProfile:
    """
    Fill in the fields the FILTER_PROFILE_ACK payload does not carry.

    A classic payload reports only the profile type, and a modern payload only
    the label. Look the profile up among those the device reports as available to
    recover the full triple. Returns the profile unchanged if no match is found.

    Args:
        profile: Profile parsed from a FILTER_PROFILE_ACK payload.
        available: Profiles reported by AVAILABLE_FILTER_PROFILES_ACK.
    """
    if not profile.label:
        for candidate in available:
            if candidate.index == profile.index:
                return candidate
        return profile

    for candidate in available:
        if candidate.label == profile.label:
            return candidate

    # A tiered selection such as "Robust/VRU" combines two profiles, and only the
    # base profile carries the type and version.
    base_label, separator, _ = profile.label.partition("/")
    if separator:
        for candidate in available:
            if candidate.label == base_label:
                return replace(candidate, label=profile.label)
    return profile


def uses_modern_filter_profile(product_code: str) -> bool:
    """
    Return True if the device selects filter profiles by ASCII label.

    SetFilterProfile has two incompatible payload formats sharing one message ID,
    and the device does not advertise which it speaks. The MTi 600-series uses
    the modern (label) form; every other family uses the classic (2-byte) form.

    Args:
        product_code: Product code reported by the device, e.g. "MTi-G-700-2A5G4".
    """
    match: re.Match[str] | None = _MTI_MODEL_PATTERN.search(product_code)
    if match is None:
        return False
    return int(match.group(1)) in _MODERN_FILTER_PROFILE_MODELS


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
        """
        Parse the device configuration from a CONFIGURATION payload.

        Args:
            payload: The 118-byte CONFIGURATION payload.
        """
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


@dataclass(frozen=True)
class MtiDeviceOutputConfig:
    """
    MTData2 output configuration exchanged via the OUTPUT_CONFIGURATION message.

    The payload is a sequence of 4-byte entries, each holding a 16-bit MTData2
    packet ID followed by a 16-bit output rate in Hz. A rate of 0xFFFF means the
    rate is ignored and the data accompanies every message.

    Packet IDs carry the format and coordinate-frame bits, so the same quantity
    in different coordinate frames are distinct entries.

    Attributes:
        rates: Mapping from MTData2 packet ID to output rate in Hz.
    """

    rates: Mapping[MtData2PacketID, int]

    @classmethod
    def from_payload(cls, payload: bytes) -> MtiDeviceOutputConfig:
        """
        Parse the output configuration from an OUTPUT_CONFIGURATION_ACK payload.

        Args:
            payload: A sequence of 4-byte packet ID and rate entries.
        """
        rates: dict[MtData2PacketID, int] = dict()
        for offset in range(0, len(payload), _OUTPUT_CONFIG_ENTRY_SIZE):
            packet_id: MtData2PacketID = MtData2PacketID(
                int.from_bytes(payload[offset : offset + 2], "big")
            )
            rates[packet_id] = int.from_bytes(payload[offset + 2 : offset + 4], "big")
        return cls(rates=rates)

    def to_payload(self) -> bytes:
        """Encode the output configuration as an OUTPUT_CONFIGURATION payload."""
        return b"".join(
            int(packet_id).to_bytes(2, "big") + rate.to_bytes(2, "big")
            for packet_id, rate in self.rates.items()
        )

    def rate_for(self, packet_id: MtData2PacketID) -> int | None:
        """
        Return the output rate for a packet ID, or None if it is not configured.

        Args:
            packet_id: The MTData2 packet ID to look up.
        """
        return self.rates.get(packet_id)

    def __contains__(self, packet_id: object) -> bool:
        return packet_id in self.rates

    def __getitem__(self, packet_id: MtData2PacketID) -> int:
        return self.rates[packet_id]

    def __iter__(self) -> Iterator[tuple[MtData2PacketID, int]]:
        return iter(self.rates.items())

    def __len__(self) -> int:
        return len(self.rates)


_OUTPUT_CONFIG_ENTRY_SIZE: int = 4

_FILTER_PROFILE_SLOT_SIZE: int = 22

_MTI_MODEL_PATTERN: re.Pattern[str] = re.compile(r"MTi-(?:G-)?(\d+)")

_MODERN_FILTER_PROFILE_MODELS: frozenset[int] = frozenset({620, 630, 670, 680})

_OPTION_FLAG_FIELDS: tuple[tuple[str, MtiDeviceOptionFlags], ...] = (
    ("disable_auto_store", _Flags.DISABLE_AUTO_STORE),
    ("disable_auto_measurement", _Flags.DISABLE_AUTO_MEASUREMENT),
    ("enable_beidou", _Flags.ENABLE_BEIDOU),
    ("enable_ahs", _Flags.ENABLE_AHS),
    ("enable_orientation_smoother", _Flags.ENABLE_ORIENTATION_SMOOTHER),
    ("enable_configurable_bus_id", _Flags.ENABLE_CONFIGURABLE_BUS_ID),
    ("enable_in_run_compass_calibration", _Flags.ENABLE_IN_RUN_COMPASS_CALIBRATION),
    ("enable_config_message_at_startup", _Flags.ENABLE_CONFIG_MESSAGE_AT_STARTUP),
    ("enable_cold_filter_resets", _Flags.ENABLE_COLD_FILTER_RESETS),
    ("enable_position_velocity_smoother", _Flags.ENABLE_POSITION_VELOCITY_SMOOTHER),
    ("enable_continuous_zru", _Flags.ENABLE_CONTINUOUS_ZRU),
)
