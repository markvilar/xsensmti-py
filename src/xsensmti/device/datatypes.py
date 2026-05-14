"""
Data types for MtiDevice state.
"""

from enum import IntEnum


class MtiDeviceState(IntEnum):
    CONFIG = 0
    MEASUREMENT = 1
