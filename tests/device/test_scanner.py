"""
Unit tests for MtiDeviceScanner.

_probe_port is mocked so no serial port is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from xsensmti.device import MtiDeviceDescriptor, MtiDeviceScanner
from xsensmti.device.datatypes import MtiDeviceInfo
from xsensmti.device import MtiPortInfo


def _make_descriptor(
    device_id: int = 0x12345678,
    port: str = "/dev/ttyUSB0",
) -> MtiDeviceDescriptor:
    return MtiDeviceDescriptor(
        port_info=MtiPortInfo(port=port, baud=115200),
        device_info=MtiDeviceInfo(
            device_id=device_id,
            product_code="MTi-700",
            firmware_version="1.0.0",
            hardware_version="2.0",
        ),
    )


class TestMtiDeviceScannerPreScan:
    def test_find_returns_none_before_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        assert scanner.find(0x12345678) is None

    def test_results_returns_empty_list_before_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        assert scanner.results() == []

    def test_device_ids_returns_empty_set_before_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        assert scanner.device_ids() == set()

    def test_len_is_zero_before_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        assert len(scanner) == 0

    def test_contains_is_false_before_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        assert 0x12345678 not in scanner


class TestMtiDeviceScannerScanPorts:
    def test_scan_ports_caches_found_device(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        assert scanner.find(0x12345678) == result

    def test_scan_ports_returns_found_devices(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scan_results: list[MtiDeviceDescriptor] = scanner.scan_ports()

        assert scan_results == [result]

    def test_scan_ports_replaces_previous_results(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        first_result: MtiDeviceDescriptor = _make_descriptor(device_id=0x11111111)
        second_result: MtiDeviceDescriptor = _make_descriptor(device_id=0x22222222)
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=first_result),
        ):
            scanner.scan_ports()

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=second_result),
        ):
            scanner.scan_ports()

        assert scanner.find(0x11111111) is None
        assert scanner.find(0x22222222) == second_result

    def test_find_returns_none_for_unknown_device(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor(device_id=0x12345678)
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        assert scanner.find(0x99999999) is None

    def test_results_returns_copy(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        copy: list[MtiDeviceDescriptor] = scanner.results()
        copy.clear()
        assert len(scanner) == 1

    def test_device_ids_returns_correct_set(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor(device_id=0x12345678)
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        assert scanner.device_ids() == {0x12345678}

    def test_len_after_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        assert len(scanner) == 1

    def test_contains_after_scan(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor(device_id=0x12345678)
        port: MagicMock = MagicMock()
        port.device = "/dev/ttyUSB0"
        port.vid = None
        port.pid = None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[port],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_ports()

        assert 0x12345678 in scanner
        assert 0x99999999 not in scanner


class TestMtiDeviceScannerScanPort:
    def test_scan_port_caches_found_device(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_port("/dev/ttyUSB0")

        assert scanner.find(0x12345678) == result

    def test_scan_port_removes_stale_entry_when_not_found(self) -> None:
        scanner: MtiDeviceScanner = MtiDeviceScanner()
        result: MtiDeviceDescriptor = _make_descriptor()

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=result),
        ):
            scanner.scan_port("/dev/ttyUSB0")

        assert scanner.find(0x12345678) is not None

        with (
            patch(
                "xsensmti.device.scanner.serial.tools.list_ports.comports",
                return_value=[],
            ),
            patch("xsensmti.device.scanner._probe_port", return_value=None),
        ):
            scanner.scan_port("/dev/ttyUSB0")

        assert scanner.find(0x12345678) is None
