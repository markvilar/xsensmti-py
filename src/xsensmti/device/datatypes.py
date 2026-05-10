"""
Data types for MtiDevice state.
"""

from enum import IntEnum


class DeviceState(IntEnum):
    CONFIG = 0
    MEASUREMENT = 1
