"""
Recorder for raw binary output from XSens MTi devices.
"""

from __future__ import annotations

import time
import serial

from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from xsensmti.xbus.datatypes import XbusMessage, XbusMessageID
from xsensmti.xbus.decode import iter_xbus_messages_from_buffer
from xsensmti.xbus.exceptions import (
    IncompletePayload,
    InvalidXbusMessageID,
    InvalidPayloadLength,
    MissingChecksum,
    MissingHeader,
)
from ..exceptions import CommandTimeout
from ..serial_io import open_serial_port, send_and_receive, send_message

_RECOVERY_TIMEOUT: float = 5.0
_RECOVERY_INTERVAL: float = 0.1


def _goto_config_mode(ser: serial.Serial, timeout: float) -> serial.Serial:
    """
    Transition the device to config mode reliably.

    Fast path: send GOTOCONFIG and wait up to `timeout` seconds for ACK.
    Fallback: send RESET then retry GOTOCONFIG every 100 ms for up to
    _RECOVERY_TIMEOUT seconds, keeping the serial handle open throughout.
    Devices typically become responsive ~1.7 s after RESET.
    """
    try:
        send_and_receive(
            ser,
            XbusMessageID.GOTOCONFIG,
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=timeout,
        )
        return ser
    except CommandTimeout:
        logger.debug(f"{ser.port}: GOTOCONFIG timed out — sending RESET and retrying")

    port: str = ser.port or ""

    try:
        ser.reset_input_buffer()
        send_message(ser, XbusMessageID.RESET)
        ser.flush()
    except (serial.SerialException, OSError):
        pass

    buf: bytearray = bytearray()
    deadline: float = time.monotonic() + _RECOVERY_TIMEOUT

    while time.monotonic() < deadline:
        try:
            send_message(ser, XbusMessageID.GOTOCONFIG)
            ser.flush()
        except (serial.SerialException, OSError):
            pass

        chunk_end: float = time.monotonic() + _RECOVERY_INTERVAL
        while time.monotonic() < chunk_end:
            try:
                chunk: bytes = ser.read(256)
                if chunk:
                    buf.extend(chunk)
            except (serial.SerialException, OSError):
                pass

        try:
            for msg in iter_xbus_messages_from_buffer(buf):
                try:
                    mid: XbusMessageID = XbusMessageID(msg.header.mid)
                except ValueError:
                    continue
                if mid == XbusMessageID.GOTOCONFIG_ACK:
                    logger.debug(f"{port}: GOTOCONFIG_ACK received after RESET")
                    return ser
        except (
            IncompletePayload,
            InvalidXbusMessageID,
            InvalidPayloadLength,
            MissingChecksum,
            MissingHeader,
        ):
            pass

    raise CommandTimeout(
        port=port,
        mid_sent=XbusMessageID.GOTOCONFIG,
        timeout=timeout + _RECOVERY_TIMEOUT,
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

        ser = _goto_config_mode(ser, timeout)

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

        with open(output, "wb", buffering=0) as f:
            try:
                while True:
                    chunk: bytes = ser.read(chunk_size)
                    if chunk:
                        f.write(chunk)
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
