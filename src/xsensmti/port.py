"""
Port identification and connection parameters for XSens MTi devices.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MtiPortInfo:
    """Connection parameters for a single MTi device."""

    port: str
    baud: int
    vid: int | None = None
    pid: int | None = None

    @property
    def is_usb(self) -> bool:
        return self.vid is not None and self.pid is not None

    @property
    def usb_info(self) -> str | None:
        if self.vid is None or self.pid is None:
            return None
        return f"VID:PID={self.vid:04X}:{self.pid:04X}"
