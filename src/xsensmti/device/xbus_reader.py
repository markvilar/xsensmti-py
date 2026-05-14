"""
XbusStreamReader — background reader for streaming Xbus messages from a serial port.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from enum import IntEnum

import serial
from loguru import logger

from xsensmti.xbus import (
    XbusMessage,
    drain_xbus_messages,
)


class XbusStreamReaderState(IntEnum):
    IDLE = 0
    RUNNING = 1
    FAULTED = 2


class XbusStreamReader:
    def __init__(
        self,
        ser: serial.Serial,
        on_message: Callable[[XbusMessage], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._ser: serial.Serial = ser
        self._on_message: Callable[[XbusMessage], None] = on_message
        self._on_error: Callable[[Exception], None] | None = on_error
        self._state: XbusStreamReaderState = XbusStreamReaderState.IDLE
        self._stop_event: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._state == XbusStreamReaderState.RUNNING:
            return
        self._stop_event.clear()
        self._state = XbusStreamReaderState.RUNNING
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name=f"xbus-reader-{self._ser.port}",
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=2.0)
        self._thread = None
        if self._state == XbusStreamReaderState.RUNNING:
            self._state = XbusStreamReaderState.IDLE

    def state(self) -> XbusStreamReaderState:
        return self._state

    def is_running(self) -> bool:
        return self._state == XbusStreamReaderState.RUNNING

    def _loop(self) -> None:
        accumulator: bytearray = bytearray()

        while not self._stop_event.is_set():
            try:
                chunk: bytes = self._ser.read(256)
            except serial.SerialException as exc:
                logger.error(f"{self._ser.port}: serial error in reader: {exc}")
                self._handle_error(exc)
                return

            if chunk:
                accumulator.extend(chunk)

            for message in drain_xbus_messages(accumulator):
                try:
                    self._on_message(message)
                except Exception as exc:
                    logger.error(f"{self._ser.port}: on_message callback raised: {exc}")
                    self._handle_error(exc)
                    return

    def _handle_error(self, exc: Exception) -> None:
        self._state = XbusStreamReaderState.FAULTED
        self._stop_event.set()
        if self._on_error is not None:
            self._on_error(exc)
