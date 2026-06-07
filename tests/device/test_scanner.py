"""
Unit tests for scanner module functions.

Serial ports and probe_port are mocked so no hardware is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from xsensmti.device import (
    MtiPortInfo,
    MtiProbeResult,
    MtiScanResult,
    probe_ports,
    scan_port,
    scan_ports,
)
from xsensmti.device.datatypes import MtiDeviceInfo


def _make_port_mock(
    device: str = "/dev/ttyUSB0",
    vid: int | None = None,
    pid: int | None = None,
) -> MagicMock:
    port: MagicMock = MagicMock()
    port.device = device
    port.vid = vid
    port.pid = pid
    return port


def _make_probe_result(
    port: str = "/dev/ttyUSB0",
    baud: int = 115200,
    device_id: int = 0x12345678,
) -> MtiProbeResult:
    return MtiProbeResult(
        port_info=MtiPortInfo(port=port, baud=baud),
        device_info=MtiDeviceInfo(
            device_id=device_id,
            product_code="MTi-700",
            firmware_version="1.0.0",
            hardware_version="2.0",
        ),
    )


class TestScanPort:
    def test_returns_scan_result_when_port_found(self) -> None:
        port_mock: MagicMock = _make_port_mock(
            device="/dev/ttyUSB0", vid=0x2639, pid=0x0017
        )
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=[port_mock],
        ):
            result: MtiScanResult | None = scan_port("/dev/ttyUSB0")

        assert result is not None
        assert result.port_info.port == "/dev/ttyUSB0"
        assert result.port_info.vid == 0x2639
        assert result.port_info.pid == 0x0017

    def test_returns_none_when_port_not_listed(self) -> None:
        port_mock: MagicMock = _make_port_mock(device="/dev/ttyUSB1")
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=[port_mock],
        ):
            result: MtiScanResult | None = scan_port("/dev/ttyUSB0")

        assert result is None

    def test_baud_is_embedded_in_port_info(self) -> None:
        port_mock: MagicMock = _make_port_mock(device="/dev/ttyUSB0")
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=[port_mock],
        ):
            result: MtiScanResult | None = scan_port("/dev/ttyUSB0", baud=921600)

        assert result is not None
        assert result.port_info.baud == 921600


class TestScanPorts:
    def test_returns_empty_list_when_no_ports(self) -> None:
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=[],
        ):
            results: list[MtiScanResult] = scan_ports()

        assert results == []

    def test_returns_one_result_per_port(self) -> None:
        mocks: list[MagicMock] = [
            _make_port_mock(device="/dev/ttyUSB0"),
            _make_port_mock(device="/dev/ttyUSB1"),
        ]
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=mocks,
        ):
            results: list[MtiScanResult] = scan_ports()

        assert len(results) == 2
        assert results[0].port_info.port == "/dev/ttyUSB0"
        assert results[1].port_info.port == "/dev/ttyUSB1"

    def test_usb_only_excludes_non_usb_ports(self) -> None:
        mocks: list[MagicMock] = [
            _make_port_mock(device="/dev/ttyUSB0", vid=0x2639, pid=0x0017),
            _make_port_mock(device="/dev/ttyS0", vid=None, pid=None),
        ]
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=mocks,
        ):
            results: list[MtiScanResult] = scan_ports(usb_only=True)

        assert len(results) == 1
        assert results[0].port_info.port == "/dev/ttyUSB0"

    def test_usb_only_false_includes_all_ports(self) -> None:
        mocks: list[MagicMock] = [
            _make_port_mock(device="/dev/ttyUSB0", vid=0x2639, pid=0x0017),
            _make_port_mock(device="/dev/ttyS0", vid=None, pid=None),
        ]
        with patch(
            "xsensmti.device.scanner.serial.tools.list_ports.comports",
            return_value=mocks,
        ):
            results: list[MtiScanResult] = scan_ports(usb_only=False)

        assert len(results) == 2


class TestProbePorts:
    def test_returns_results_for_found_devices(self) -> None:
        port_infos: list[MtiPortInfo] = [
            MtiPortInfo(port="/dev/ttyUSB0", baud=115200),
        ]
        probe_result: MtiProbeResult = _make_probe_result()

        with patch(
            "xsensmti.device.scanner.probe_port",
            return_value=probe_result,
        ):
            results: list[MtiProbeResult] = probe_ports(port_infos)

        assert results == [probe_result]

    def test_excludes_ports_where_probe_returns_none(self) -> None:
        port_infos: list[MtiPortInfo] = [
            MtiPortInfo(port="/dev/ttyUSB0", baud=115200),
            MtiPortInfo(port="/dev/ttyUSB1", baud=115200),
        ]
        found: MtiProbeResult = _make_probe_result(port="/dev/ttyUSB0")

        def _side_effect(
            port_info: MtiPortInfo, timeout: float
        ) -> MtiProbeResult | None:
            if port_info.port == "/dev/ttyUSB0":
                return found
            return None

        with patch(
            "xsensmti.device.scanner.probe_port",
            side_effect=_side_effect,
        ):
            results: list[MtiProbeResult] = probe_ports(port_infos)

        assert results == [found]

    def test_returns_empty_list_when_no_devices_found(self) -> None:
        port_infos: list[MtiPortInfo] = [
            MtiPortInfo(port="/dev/ttyUSB0", baud=115200),
        ]
        with patch(
            "xsensmti.device.scanner.probe_port",
            return_value=None,
        ):
            results: list[MtiProbeResult] = probe_ports(port_infos)

        assert results == []

    def test_returns_empty_list_when_no_ports_given(self) -> None:
        results: list[MtiProbeResult] = probe_ports([])
        assert results == []
