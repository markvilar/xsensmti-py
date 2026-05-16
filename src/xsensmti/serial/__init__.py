"""
Low-level serial communication primitives for XSens MTi devices.
"""

from .serial_io import (
    open_serial_port as open_serial_port,
    send_message as send_message,
    receive_message as receive_message,
    send_and_receive as send_and_receive,
)
from .operations import (
    goto_config_mode as goto_config_mode,
    goto_measurement_mode as goto_measurement_mode,
)

__all__: list[str] = []
