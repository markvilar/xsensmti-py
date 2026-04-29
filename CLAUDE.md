# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A minimal Python library for working with XSens MTi sensors, implementing the Xbus and MTData2 binary communication protocols.

## Skills

When developing Python code in this project, use these skills at the appropriate moments:

- `/python-library-complete:api-design` — before finalising any new public interface (functions, types, exceptions). Use it to evaluate naming, composability, and error handling before the design is locked in.
- `/python-library-complete:code-quality` — after implementing a module or non-trivial function. Use it to check for Pythonic idioms, type hint completeness, and mypy strictness issues that ruff won't catch.
- `/python-library-complete:testing-strategy` — when adding a new module or a protocol feature with structured input space. Use it to design fixtures, parametrization, and property-based tests before writing test code.

## Conventions

- All Python code uses type hints on variables, function arguments, and return types.
- Use the Python 3.12 `type` statement for type aliases: `type Alias = SomeType`.

## Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/xbus/test_package.py::test_can_import_xsens_xbus

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Build
uv build
```

## Architecture

The library lives under `src/xsens/` as a namespace package with two protocol modules:

**`xbus/`** — parses the Xbus binary framing layer used by XSens devices over serial.
- `datatypes.py` — enums and dataclasses: `MessageID`, `XbusFraming`, `PayloadLength`, `XbusMessage`, `XbusMessageHeader`
- `decode.py` — core parsing: `decode_xbus_messages_from_buffer()` and `iter_xbus_messages_from_buffer()` validate checksums and extract `XbusMessage` instances from raw `bytes`
- `exceptions.py` — domain exceptions: `MissingHeader`, `InvalidChecksum`, etc.

**`mtdata2/`** — defines the MTData2 output data format that rides inside Xbus message payloads.
- `datatypes.py` — `OutputDataIdentifier` enum (quaternion, euler angles, acceleration, rate of turn, GNSS/INS data, etc.) and `OutputDataPacket`

All data types across both modules use `@dataclass(frozen=True)` — follow this pattern when adding new types.

**Scripts** (`scripts/`) — standalone CLI tools using Click for recording data from serial (`record_chunks.py`) and replaying binary captures (`replay_chunks.py`, `replay_xbus_messages.py`). Not part of the installed library.

**Test data** (`data/`) — binary `.bin` recordings used for integration-style testing and script replay.

The typical data flow is: raw serial bytes → `decode_xbus_messages_from_buffer()` → `XbusMessage` list → parse payload as `OutputDataPacket` using `OutputDataIdentifier`.

## Device interaction

When working with a physical XSens MTi sensor on `/dev/ttyUSB0`:

```bash
lsusb                                              # list USB devices
screen /dev/ttyUSB0 115200                         # view serial output
dd if=/dev/ttyUSB0 of=dump.bin bs=1M status=progress  # capture raw binary
fuser -v /dev/ttyUSB0                              # find processes holding the port
```
