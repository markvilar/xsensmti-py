"""
Public API for xsens.tools — CLI helpers for MTi sensor configuration.
"""

from xsensmti.exceptions import (
    XsensError as XsensError,
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

from xsensmti.port import MtiPortInfo as MtiPortInfo
from .scanner import (
    ScanOptions as ScanOptions,
    scan_port as scan_port,
    scan_ports as scan_ports,
)

from .recorder import (
    RecordingResult as RecordingResult,
    record_device as record_device,
)

__all__ = []
