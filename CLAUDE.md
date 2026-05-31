# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Python library for working with XSens MTi sensors, implementing the Xbus and MTData2 binary communication protocols, and device communication and control.

## Behavioral guidelines

These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### Think before coding

Before implementing, state assumptions explicitly — if uncertain, ask. If multiple interpretations exist, present them rather than picking silently. If a simpler approach exists, say so. If something is unclear, stop, name what's confusing, and ask.

### Simplicity first

Write the minimum code that solves the problem. No features beyond what was asked, no abstractions for single-use code, no unrequested flexibility or configurability, no error handling for impossible scenarios. If 200 lines could be 50, rewrite it.

### Surgical changes

Touch only what the request requires. Don't improve adjacent code, comments, or formatting. Don't refactor things that aren't broken. Match existing style. If unrelated dead code is noticed, mention it — don't delete it. Remove imports, variables, and functions that your changes made unused, but leave pre-existing dead code alone unless asked. Every changed line should trace directly to the user's request.

### Goal-driven execution

Transform tasks into verifiable goals before starting:

- "Add validation" → write tests for invalid inputs, then make them pass
- "Fix the bug" → write a test that reproduces it, then make it pass
- "Refactor X" → ensure tests pass before and after

For multi-step tasks, state a brief plan with a verification check per step.

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

After implementing changes, always run `uv run ruff check .`, `uv run ruff format .`, and `uv run mypy .`.

### Type hints

Always add type hints to variables, function arguments, and return types. Use the Python 3.12 `type` statement for type aliases: `type Alias = SomeType`.

### Variable names

Prefer full words over abbreviations for variable names — use `message` not `msg`, `packet` not `pkt`, `result` not `res`, `error` not `err`, `config` not `cfg`, and so on. This applies to names of any length; three-character abbreviations are just as discouraged as one- or two-character ones. Exception: short or single-character names are acceptable for class member fields (e.g. `x`, `y`, `z`, `w` on a quaternion dataclass).

### Docstrings

Under "Arguments", "Returns", and "Attributes" section headers, add a line of hyphens and do not indent the descriptions.

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


@dataclass(frozen=True)
class XbusMessage:
    """
    A parsed Xbus protocol message.

    Attributes
    ----------
    mid: Message identifier.
    payload: Raw payload bytes.
    """

    mid: XbusMessageID
    payload: bytes
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

The XSens MT SDK (C++) is available at https://github.com/markvilar/xsens-sdk — useful for understanding the reference architecture (`XsControl`, `XsDevice`, `XsCallback`, `XsDataPacket`) when making design decisions for this library.

XSens product documentation is available under `docs/xsens/`:

- `xsens_mti_family_reference_manual.pdf` — MTi family reference manual
- `xsens_mti_low_level_documentation.pdf` — low-level Xbus protocol documentation
- `xsens_mti_600_series_user_manual.pdf` — MTi 600-series (includes MTi 700) user manual
- `xsens_mti_10_100_series_user_manual.pdf` — MTi 10/100-series user manual
- `xsens_mti_usermanual.pdf` — general MTi user manual

### Definition order

Keep public classes and functions closer to the top of the file, and private classes and functions further down. This is safe in Python since function bodies are resolved at call time, not definition time.

### Dictionary initialization

Use `dict()` rather than `{}` to initialize empty dictionaries. The `C408` ruff rule is not enabled in this project.

## Git conventions

Never reference Claude in git commit messages, pull requests, or issues. This includes `Co-Authored-By` trailers, body text, or any other attribution to Claude or Anthropic.

## GitHub issues

When writing GitHub issue bodies via `gh issue create` or `gh issue edit`, use bare backticks (`` ` ``) for inline code and code fences. Do **not** escape them as `` \` `` — the shell heredoc passes the body verbatim to the API and escaped backticks will appear literally in the rendered issue.

## Device interaction

When working with a physical XSens MTi sensor on `/dev/ttyUSB0`:

```bash
lsusb                                              # list USB devices
screen /dev/ttyUSB0 115200                         # view serial output
dd if=/dev/ttyUSB0 of=dump.bin bs=1M status=progress  # capture raw binary
fuser -v /dev/ttyUSB0                              # find processes holding the port
```
