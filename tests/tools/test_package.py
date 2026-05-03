"""
Import smoke tests for xsens.tools.
"""

from __future__ import annotations


def test_can_import_xsens_tools() -> None:
    import xsens.tools  # noqa: F401


def test_can_import_cli_without_side_effects() -> None:
    from xsens.tools.cli.commands import main

    assert callable(main)


def test_can_import_exceptions() -> None:
    from xsens.tools import (
        CommandTimeout,
        ConfigurationError,
        DeviceNotFound,
        UnexpectedResponse,
        XsensToolsError,
    )

    assert issubclass(DeviceNotFound, XsensToolsError)
    assert issubclass(CommandTimeout, XsensToolsError)
    assert issubclass(UnexpectedResponse, XsensToolsError)
    assert issubclass(ConfigurationError, XsensToolsError)


def test_can_import_presets() -> None:
    from xsens.tools import PRESET_NAMES

    assert "gnss" in PRESET_NAMES
