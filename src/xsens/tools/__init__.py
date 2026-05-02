"""
Public API for xsens.tools — CLI helpers for MTi sensor configuration.
"""

from .exceptions import (
    XsensToolsError as XsensToolsError,
    DeviceNotFound as DeviceNotFound,
    CommandTimeout as CommandTimeout,
    UnexpectedResponse as UnexpectedResponse,
    ConfigurationError as ConfigurationError,
)

from .configurator.presets import (
    PRESET_NAMES as PRESET_NAMES,
    VALID_RATES as VALID_RATES,
    get_preset as get_preset,
    build_output_configuration_payload as build_output_configuration_payload,
)

from .configurator import configure_device as configure_device

from .scanner import (
    ScanResult as ScanResult,
    scan_ports as scan_ports,
)

__all__ = []
