"""
Recorder for raw binary output from XSens MTi devices.
"""

from __future__ import annotations

import time
import serial

from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
)
from xsensmti.serial import (
    goto_config_mode,
    open_serial_port,
    send_and_receive,
)


@dataclass(frozen=True)
class RecordingResult:
    """Summary of a completed recording session."""

    port: str
    device_id: int
    output_path: Path
    bytes_recorded: int
    duration: float


def record_device(
    port: str,
    output: Path,
    baud: int = 115200,
    timeout: float = 5.0,
    chunk_size: int = 4096,
) -> RecordingResult:
    """
    Verify an MTi device on port, then stream its output to a binary file.

    Transitions the device to measurement mode after confirming its identity,
    then reads raw serial bytes in chunks and writes them to output. Stops
    cleanly on KeyboardInterrupt (Ctrl-C). Raises domain exceptions if the
    device handshake fails; caller is responsible for handling them.
    """
    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, baud, read_timeout=0.1)
        ser.reset_input_buffer()

        goto_config_mode(ser, timeout)

        device_id_msg: XbusMessage = send_and_receive(
            ser,
            XbusMessageID.REQ_DEVICE_ID,
            expected_mid=XbusMessageID.DEVICE_ID,
            timeout=timeout,
        )
        device_id: int = int.from_bytes(device_id_msg.payload, "big")
        logger.info(f"Device ID: {device_id:#010x}")

        send_and_receive(
            ser,
            XbusMessageID.GOTOMEASUREMENT,
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
            timeout=timeout,
        )
        logger.info(f"Recording to {output} — press Ctrl-C to stop.")

        output.parent.mkdir(parents=True, exist_ok=True)

        bytes_recorded: int = 0
        start: float = time.monotonic()

        with open(output, "wb", buffering=0) as output_file:
            try:
                while True:
                    chunk: bytes = ser.read(chunk_size)
                    if chunk:
                        output_file.write(chunk)
                        bytes_recorded += len(chunk)
            except KeyboardInterrupt:
                pass

        duration: float = time.monotonic() - start
        rate: float = bytes_recorded / duration if duration > 0 else 0.0
        logger.info(
            f"Recorded {bytes_recorded} bytes in {duration:.1f}s ({rate:.0f} B/s)."
        )

        return RecordingResult(
            port=port,
            device_id=device_id,
            output_path=output,
            bytes_recorded=bytes_recorded,
            duration=duration,
        )

    finally:
        if ser is not None:
            ser.close()
