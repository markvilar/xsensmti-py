# xsensmti

A Python library for working with XSens MTi sensors: the Xbus and MTData2 binary
protocols, plus device communication and control.

!!! info "Version"

    This documentation describes **xsensmti {{ library_version }}**.

## Installation

```shell
uv add xsensmti
```

## Quick start

Find a device, read its configuration, and stream measurements.

```python
from xsensmti.device import MtiPortInfo, MtiSession

with MtiSession(MtiPortInfo(port="/dev/ttyUSB0", baud=115200)) as device:
    info = device.device_info()
    print(f"{info.product_code} (firmware {info.firmware_version})")

    config = device.request_output_config()
    for packet_id, rate in config:
        print(f"{packet_id.name}: {rate} Hz")
```

If the baud rate is unknown, discover it — nothing is written to the device:

```python
from xsensmti.device import discover_baudrate

baud = discover_baudrate("/dev/ttyUSB0")
```

## Layout

The library is organised around the two protocol layers and the device API built on
top of them.

| Package | Purpose |
| --- | --- |
| [`xsensmti.xbus`](api/xbus.md) | Xbus binary framing: message IDs, encoding, decoding, checksums |
| [`xsensmti.mtdata2`](api/mtdata2.md) | MTData2 output format carried inside Xbus payloads |
| [`xsensmti.device`](api/device.md) | `MtiDevice` / `AsyncMtiDevice`, configuration, scanning |
| [`xsensmti.serial`](api/serial.md) | Serial port helpers |
| [`xsensmti.tools`](api/tools.md) | CLI helpers for configuration and recording |
| [`xsensmti.exceptions`](api/exceptions.md) | Domain exceptions |

The typical data flow is: raw serial bytes → `decode_xbus_messages_from_buffer()` →
`XbusMessage` → decoded measurements.
