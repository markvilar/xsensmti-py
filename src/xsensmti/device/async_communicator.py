"""
AsyncMtiDeviceCommunicator — async serial port owner and XbusStreamReader bridge.
"""

from __future__ import annotations

import asyncio
import serial

from collections.abc import Callable, Coroutine
from typing import Any
from loguru import logger
from xsensmti.serial import (
    open_serial_port,
    send_and_receive as serial_send_and_receive,
    send_message,
)
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    build_xbus_command,
)
from .datatypes import MtiDeviceInfo, MtiPortInfo
from .xbus_reader import XbusStreamReader


type AsyncXbusMessageCallback = Callable[[XbusMessage], Coroutine[Any, Any, None]]
type AsyncErrorCallback = Callable[[Exception], Coroutine[Any, Any, None]]

_QUEUE_MAX_SIZE: int = 256


class AsyncMtiDeviceCommunicator:
    """
    Async counterpart to MtiDeviceCommunicator.

    Owns a pyserial port and an XbusStreamReader background thread. The reader
    thread bridges received messages into the asyncio event loop via an
    asyncio.Queue, which is drained by an internal dispatch task that calls the
    registered async message callback.

    Construct with the `create()` classmethod — not `__init__` directly.

    Attributes:
        _ser: Open pyserial port. Blocking calls are offloaded via asyncio.to_thread.
        _reader: Background thread reading Xbus messages from the serial port.
        _loop: Event loop captured at construction time for call_soon_threadsafe.
        _queue: Thread-to-loop bridge. The reader thread enqueues; the dispatch task dequeues.
        _dispatch_task: Asyncio task that drains the queue and fires the message callback.
        _message_callback: Async callable invoked for each received XbusMessage.
        _error_callback: Async callable invoked when the reader thread or dispatch task faults.
    """

    _port_info: MtiPortInfo
    _device_info: MtiDeviceInfo
    _timeout: float
    _ser: serial.Serial
    _loop: asyncio.AbstractEventLoop
    _queue: asyncio.Queue[XbusMessage]
    _reader: XbusStreamReader
    _dispatch_task: asyncio.Task[None]
    _message_callback: AsyncXbusMessageCallback | None
    _error_callback: AsyncErrorCallback | None

    @classmethod
    async def create(
        cls,
        port_info: MtiPortInfo,
        device_info: MtiDeviceInfo,
        timeout: float = 5.0,
    ) -> AsyncMtiDeviceCommunicator:
        """
        Open a serial port and return a ready-to-use communicator.

        Opens the port, resets the input buffer, sends GOTOCONFIG, and starts
        the internal dispatch task. Raises on serial or Xbus errors.

        Args:
            port_info: Connection parameters for the serial port to open.
            device_info: Identity information for the device on this port.
            timeout: Default timeout in seconds for Xbus send-and-receive calls.

        Returns:
            A fully initialised AsyncMtiDeviceCommunicator in config state.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        queue: asyncio.Queue[XbusMessage] = asyncio.Queue(maxsize=_QUEUE_MAX_SIZE)

        ser: serial.Serial = await asyncio.to_thread(
            open_serial_port, port_info.port, port_info.baud, read_timeout=0.1
        )
        await asyncio.to_thread(ser.reset_input_buffer)

        communicator: AsyncMtiDeviceCommunicator = cls.__new__(cls)
        communicator._port_info = port_info
        communicator._device_info = device_info
        communicator._timeout = timeout
        communicator._ser = ser
        communicator._loop = loop
        communicator._queue = queue
        communicator._message_callback = None
        communicator._error_callback = None

        communicator._reader = XbusStreamReader(
            ser=ser,
            on_message=communicator._on_reader_message,
            on_error=communicator._on_reader_error,
        )

        dispatch_task: asyncio.Task[None] = asyncio.create_task(
            communicator._dispatch_loop(),
            name=f"dispatch-{port_info.port}",
        )
        dispatch_task.add_done_callback(communicator._on_dispatch_task_done)
        communicator._dispatch_task = dispatch_task

        try:
            await communicator.goto_config()
        except Exception:
            await communicator.close()
            raise

        return communicator

    # --- Identity ---

    @property
    def port(self) -> str:
        return str(self._ser.port)

    def port_info(self) -> MtiPortInfo:
        return self._port_info

    def device_info(self) -> MtiDeviceInfo:
        return self._device_info

    # --- Callback registration ---

    def set_message_callback(self, callback: AsyncXbusMessageCallback) -> None:
        self._message_callback = callback

    def set_error_callback(self, callback: AsyncErrorCallback) -> None:
        self._error_callback = callback

    # --- Communication ---

    async def send(self, message: XbusMessage) -> None:
        """
        Send an Xbus message without waiting for a response.

        Args:
            message: The Xbus message to write to the serial port.
        """
        await asyncio.to_thread(send_message, self._ser, message)

    async def send_and_receive(
        self,
        message: XbusMessage,
        expected_mid: XbusMessageID,
        timeout: float | None = None,
    ) -> XbusMessage:
        """
        Send an Xbus message and wait for its acknowledgement.

        Args:
            message: The Xbus message to send.
            expected_mid: Message ID of the expected response.
            timeout: Maximum seconds to wait for a response. Defaults to the communicator timeout.

        Returns:
            The first matching XbusMessage received before the deadline.
        """
        effective_timeout: float = timeout if timeout is not None else self._timeout
        return await asyncio.to_thread(
            serial_send_and_receive,
            self._ser,
            message,
            expected_mid=expected_mid,
            timeout=effective_timeout,
        )

    # --- State transitions ---

    async def goto_config(self) -> None:
        """Stop the stream reader and put the device in config state."""
        await asyncio.to_thread(self._reader.stop)
        await self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOCONFIG),
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
        )

    async def goto_measurement(self) -> None:
        """Put the device in measurement state and start the stream reader."""
        await self.send_and_receive(
            build_xbus_command(XbusMessageID.GOTOMEASUREMENT),
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
        )
        self._reader.start()

    # --- Port management ---

    def flush(self) -> None:
        """Reset the serial input buffer."""
        self._ser.reset_input_buffer()

    async def close(self) -> None:
        """Cancel the dispatch task, stop the reader, and close the serial port."""
        self._dispatch_task.cancel()
        try:
            await self._dispatch_task
        except (asyncio.CancelledError, Exception):
            pass
        await asyncio.to_thread(self._reader.stop)
        await asyncio.to_thread(self._ser.close)

    # --- Internal ---

    def _on_reader_message(self, message: XbusMessage) -> None:
        """Called from XbusStreamReader thread — schedules enqueue on the event loop."""
        self._loop.call_soon_threadsafe(self._enqueue_message, message)

    def _on_reader_error(self, exc: Exception) -> None:
        """Called from XbusStreamReader thread — schedules error dispatch on the event loop."""
        self._loop.call_soon_threadsafe(self._dispatch_error, exc)

    def _enqueue_message(self, message: XbusMessage) -> None:
        """Drop the oldest message if the queue is full, then enqueue the new one."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    def _dispatch_error(self, exc: Exception) -> None:
        """Fire the error callback as a fire-and-forget task."""
        logger.error(f"{self.port}: reader error: {exc}")
        if self._error_callback is not None:
            asyncio.ensure_future(self._error_callback(exc))

    async def _dispatch_loop(self) -> None:
        while True:
            message: XbusMessage = await self._queue.get()
            if self._message_callback is not None:
                await self._message_callback(message)

    def _on_dispatch_task_done(self, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc: BaseException | None = task.exception()
        if exc is None:
            return
        logger.error(f"{self.port}: dispatch task raised: {exc}")
        if self._error_callback is not None:
            asyncio.ensure_future(self._error_callback(exc))  # type: ignore[arg-type]
