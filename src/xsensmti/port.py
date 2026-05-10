"""
Port identification and connection parameters for XSens MTi devices.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MtiPortInfo:
    """Port and device identity for a single MTi connection."""

    port: str
    baud: int
    device_id: int = 0
    product_code: str = ""
    vid: int | None = None
    pid: int | None = None

    @property
    def is_usb(self) -> bool:
        return self.vid is not None and self.pid is not None

    @property
    def is_identified(self) -> bool:
        return self.device_id != 0

    @property
    def usb_info(self) -> str | None:
        if self.vid is None or self.pid is None:
            return None
        return f"VID:PID={self.vid:04X}:{self.pid:04X}"
