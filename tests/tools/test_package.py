"""
Import smoke tests for xsens.tools.
"""

from __future__ import annotations


def test_can_import_xsens_tools() -> None:
    import xsensmti.tools  # noqa: F401


def test_can_import_cli_without_side_effects() -> None:
    from xsensmti.tools.cli.commands import main

    assert callable(main)


def test_can_import_exceptions() -> None:
    from xsensmti.tools import (
        CommandTimeout,
        ConfigurationError,
        DeviceNotFound,
        UnexpectedResponse,
        XsensError,
    )

    assert issubclass(DeviceNotFound, XsensError)
    assert issubclass(CommandTimeout, XsensError)
    assert issubclass(UnexpectedResponse, XsensError)
    assert issubclass(ConfigurationError, XsensError)


def test_can_import_presets() -> None:
    from xsensmti.tools import PRESET_NAMES

    assert "gnss" in PRESET_NAMES
