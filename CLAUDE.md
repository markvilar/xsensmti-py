# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A minimal Python library for working with XSens MTi sensors, implementing the Xbus and MTData2 binary communication protocols.

## Skills

When developing Python code in this project, use these skills at the appropriate moments:

- `/python-library-complete:api-design` — before finalising any new public interface (functions, types, exceptions). Use it to evaluate naming, composability, and error handling before the design is locked in.
- `/python-library-complete:code-quality` — after implementing a module or non-trivial function. Use it to check for Pythonic idioms, type hint completeness, and mypy strictness issues that ruff won't catch.
- `/python-library-complete:testing-strategy` — when adding a new module or a protocol feature with structured input space. Use it to design fixtures, parametrization, and property-based tests before writing test code.

## Python coding style

### Import ordering

Group imports in this order. Separate the `import ...` groups from the `from ... import ...` groups with a blank line.

1. `import <stdlib>`
2. `import <external>`
3. `import <internal>`

4. `from <stdlib> import ...`
5. `from <external> import ...`
6. `from <internal> import ...`

### Strings

Use double quotes for all strings. Single quotes are acceptable inside f-strings to avoid escaping.

### Internal package imports

When importing from internal packages, import classes and functions from the package, not from the module within it. This decouples callers from the internal file layout.

```python
# Preferred
from xsensmti.xbus import XbusMessage, XbusMessageID

# Avoid
from xsensmti.xbus.datatypes import XbusMessage, XbusMessageID
```

### Tooling

- **Linting:** `uv run ruff check .`
- **Formatting:** `uv run ruff format .`
- **Type checking:** `uv run mypy .`
- **Tests:** `uv run pytest`

### Type hints

Always add type hints to variables, function arguments, and return types. Use the Python 3.12 `type` statement for type aliases: `type Alias = SomeType`.

### Variable names

Prefer not to use single- or two-character abbreviations for variable names, as descriptive names make the code more readable. Exception: short or single-character names are acceptable for class member fields (e.g. `x`, `y`, `z`, `w` on a quaternion dataclass).

### Docstrings

Under "Arguments" and "Returns" section headers, add a line of hyphens and do not indent the descriptions.

```python
def send_and_receive(
    ser: serial.Serial,
    mid: XbusMessageID,
    timeout: float = 2.0,
) -> XbusMessage:
    """
    Send an Xbus message and wait for its acknowledgement.

    Arguments
    ---------
    ser: Open serial port to write to and read from.
    mid: Message ID of the command to send.
    timeout: Maximum seconds to wait for a response.

    Returns
    -------
    The first matching XbusMessage received before the deadline.
    """
```

### Multi-item imports

When importing multiple names from the same package or module, use parentheses with one name per line.

```python
from xsensmti.xbus import (
    XbusMessage,
    XbusMessageID,
    encode_xbus_message,
    iter_xbus_messages_from_buffer,
)
```

## Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/xbus/test_package.py::test_can_import_xsensmti_xbus

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Build
uv build
```

## Architecture

The library lives under `src/xsensmti/` as a namespace package with two protocol modules:

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

## Documentation

XSens product documentation is available under `docs/xsens/`:

- `xsens_mti_family_reference_manual.pdf` — MTi family reference manual
- `xsens_mti_low_level_documentation.pdf` — low-level Xbus protocol documentation
- `xsens_mti_600_series_user_manual.pdf` — MTi 600-series (includes MTi 700) user manual
- `xsens_mti_10_100_series_user_manual.pdf` — MTi 10/100-series user manual
- `xsens_mti_usermanual.pdf` — general MTi user manual

## Device interaction

When working with a physical XSens MTi sensor on `/dev/ttyUSB0`:

```bash
lsusb                                              # list USB devices
screen /dev/ttyUSB0 115200                         # view serial output
dd if=/dev/ttyUSB0 of=dump.bin bs=1M status=progress  # capture raw binary
fuser -v /dev/ttyUSB0                              # find processes holding the port
```
