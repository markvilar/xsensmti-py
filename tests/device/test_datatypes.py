"""
Tests for MtiDeviceOptions, MtiDeviceFilterProfile, and MtiDeviceConfig parsers.
"""

import pytest

from xsensmti.device import (
    MtiDeviceConfig,
    MtiDeviceFilterProfile,
    MtiDeviceOptions,
)


# ---------------------------------------------------------------------------
# MtiDeviceOptions
# ---------------------------------------------------------------------------


def _options_payload(flags: int) -> bytes:
    return flags.to_bytes(4, "big")


def test_options_all_clear() -> None:
    options = MtiDeviceOptions.from_payload(_options_payload(0x00000000))
    assert not options.disable_auto_store
    assert not options.disable_auto_measurement
    assert not options.enable_beidou
    assert not options.enable_ahs
    assert not options.enable_orientation_smoother
    assert not options.enable_configurable_bus_id
    assert not options.enable_in_run_compass_calibration
    assert not options.enable_config_message_at_startup
    assert not options.enable_cold_filter_resets
    assert not options.enable_position_velocity_smoother
    assert not options.enable_continuous_zru


def test_options_all_set() -> None:
    options = MtiDeviceOptions.from_payload(_options_payload(0xFFFFFFFF))
    assert options.disable_auto_store
    assert options.disable_auto_measurement
    assert options.enable_beidou
    assert options.enable_ahs
    assert options.enable_orientation_smoother
    assert options.enable_configurable_bus_id
    assert options.enable_in_run_compass_calibration
    assert options.enable_config_message_at_startup
    assert options.enable_cold_filter_resets
    assert options.enable_position_velocity_smoother
    assert options.enable_continuous_zru


@pytest.mark.parametrize(
    "flag, field",
    [
        (0x00000001, "disable_auto_store"),
        (0x00000002, "disable_auto_measurement"),
        (0x00000004, "enable_beidou"),
        (0x00000010, "enable_ahs"),
        (0x00000020, "enable_orientation_smoother"),
        (0x00000040, "enable_configurable_bus_id"),
        (0x00000080, "enable_in_run_compass_calibration"),
        (0x00000200, "enable_config_message_at_startup"),
        (0x00000400, "enable_cold_filter_resets"),
        (0x00000800, "enable_position_velocity_smoother"),
        (0x00001000, "enable_continuous_zru"),
    ],
)
def test_options_single_flag(flag: int, field: str) -> None:
    options = MtiDeviceOptions.from_payload(_options_payload(flag))
    assert getattr(options, field) is True
    for other_field in vars(options):
        if other_field != field:
            assert getattr(options, other_field) is False


# ---------------------------------------------------------------------------
# MtiDeviceFilterProfile
# ---------------------------------------------------------------------------


def test_filter_profile_classic_two_bytes() -> None:
    profile = MtiDeviceFilterProfile.from_payload(bytes([1, 39]))
    assert profile.version == 1
    assert profile.index == 39
    assert profile.label == ""


def test_filter_profile_modern_simple_label() -> None:
    profile = MtiDeviceFilterProfile.from_payload(b"General")
    assert profile.label == "General"
    assert profile.version == 0
    assert profile.index == 0


def test_filter_profile_modern_combined_label() -> None:
    profile = MtiDeviceFilterProfile.from_payload(b"Robust/VRU")
    assert profile.label == "Robust/VRU"


def test_filter_profile_modern_label_strips_trailing_spaces() -> None:
    profile = MtiDeviceFilterProfile.from_payload(b"General   ")
    assert profile.label == "General"


# ---------------------------------------------------------------------------
# MtiDeviceConfig
# ---------------------------------------------------------------------------

_OLDER_SERIES_PAYLOAD = (
    b"\x00\x12\x34\x56"  # device ID (4 bytes, non-zero first byte)
    + b"\x04\x80"  # sampling period = 0x0480 = 1152 (100 Hz)
    + b"\x00\x00"  # output skip factor = 0
    + b"\x00" * 88  # syncin + date + time + reserved (88 bytes)
    + b"\x00\x01"  # num_devices = 1  (offset 96)
    + b"\x00" * 6  # device ID (4 bytes) + data length (2 bytes)
    + b"\x00\x06"  # output mode = 6  (offset 104)
    + b"\x00\x00\x00\x30"  # output settings = 0x30 (offset 106)
    + b"\x00" * 8  # reserved
)

_MTI600_PAYLOAD = (
    b"\x00\x00\x00\x00"  # first 4 bytes zero → MTi-600 layout
    + b"\x12\x34\x56\x78"  # remaining 4 bytes of 8-byte device ID
    + b"\x00" * 88  # syncin + date + time + reserved (88 bytes)
    + b"\x00\x01"  # num_devices = 1  (offset 96)
    + b"\x00" * 20  # device ID (8 bytes) + reserved (12 bytes)
)


def test_config_older_series_parses_fields() -> None:
    assert len(_OLDER_SERIES_PAYLOAD) == 118
    config = MtiDeviceConfig.from_payload(_OLDER_SERIES_PAYLOAD)
    assert config.num_devices == 1
    assert config.sampling_period == 0x0480
    assert config.output_skip_factor == 0
    assert config.output_mode == 6
    assert config.output_settings == 0x30


def test_config_mti600_has_none_fields() -> None:
    assert len(_MTI600_PAYLOAD) == 118
    config = MtiDeviceConfig.from_payload(_MTI600_PAYLOAD)
    assert config.num_devices == 1
    assert config.sampling_period is None
    assert config.output_skip_factor is None
    assert config.output_mode is None
    assert config.output_settings is None
