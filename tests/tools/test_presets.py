"""
Unit tests for output configuration presets.
"""

from __future__ import annotations

import struct
import pytest

from xsensmti.mtdata2.datatypes import OutputDataIdentifier
from xsensmti.xbus.decode import is_frame_checksum_valid
from xsensmti.xbus.encode import encode_xbus_message
from xsensmti.xbus.datatypes import XbusMessageID
from xsensmti.tools.configurator.presets import (
    PRESET_NAMES,
    VALID_RATES,
    build_output_configuration_payload,
    get_preset,
)


class TestGetPreset:
    def test_returns_tuple_of_pairs(self) -> None:
        preset = get_preset("imu")
        assert isinstance(preset, tuple)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in preset)

    def test_imu_preset_contains_expected_xdis(self) -> None:
        xdis = {xdi for xdi, _ in get_preset("imu")}
        assert OutputDataIdentifier.ACCELERATION in xdis
        assert OutputDataIdentifier.RATE_OF_TURN in xdis
        assert OutputDataIdentifier.MAGNETIC_FIELD in xdis

    def test_vru_preset_contains_quaternion(self) -> None:
        xdis = {xdi for xdi, _ in get_preset("vru")}
        assert OutputDataIdentifier.ORIENTATION_QUATERNION in xdis

    def test_gnss_preset_contains_position_and_velocity(self) -> None:
        xdis = {xdi for xdi, _ in get_preset("gnss")}
        assert OutputDataIdentifier.POSITION_LL_ELLIPSOID in xdis
        assert OutputDataIdentifier.VELOCITY_NED in xdis

    def test_gnss_pvt_capped_at_4hz(self) -> None:
        for xdi, rate in get_preset("gnss", rate=100):
            if xdi == OutputDataIdentifier.GNSS_PVT:
                assert rate == 4

    def test_other_outputs_use_requested_rate(self) -> None:
        for xdi, rate in get_preset("gnss", rate=50):
            if xdi != OutputDataIdentifier.GNSS_PVT:
                assert rate == 50

    def test_raises_for_unknown_preset(self) -> None:
        with pytest.raises(ValueError, match="unknown preset"):
            get_preset("unknown")

    def test_raises_for_invalid_rate(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            get_preset("imu", rate=99)

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_all_presets_valid(self, name: str) -> None:
        preset = get_preset(name)
        assert len(preset) > 0

    @pytest.mark.parametrize("rate", sorted(VALID_RATES))
    def test_all_valid_rates_accepted(self, rate: int) -> None:
        get_preset("imu", rate=rate)


class TestBuildOutputConfigurationPayload:
    def test_payload_length_is_4_bytes_per_output(self) -> None:
        preset = get_preset("imu")
        payload = build_output_configuration_payload(preset)
        assert len(payload) == len(preset) * 4

    def test_payload_encodes_xdi_and_rate(self) -> None:
        preset = get_preset("imu", rate=100)
        payload = build_output_configuration_payload(preset)
        for i, (xdi, rate) in enumerate(preset):
            xdi_encoded, rate_encoded = struct.unpack_from(">HH", payload, offset=i * 4)
            assert xdi_encoded == int(xdi)
            assert rate_encoded == rate

    def test_full_frame_has_valid_checksum(self) -> None:
        for name in PRESET_NAMES:
            preset = get_preset(name)
            payload = build_output_configuration_payload(preset)
            frame = encode_xbus_message(
                XbusMessageID.OUTPUT_CONFIGURATION, payload=payload
            )
            assert is_frame_checksum_valid(
                frame
            ), f"invalid checksum for preset '{name}'"
