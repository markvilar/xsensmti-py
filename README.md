# XSens-MTi Python Library

![ci](https://github.com/markvilar/xsens-py/actions/workflows/ubuntu.yml/badge.svg)


### Getting started

#### Installing `uv`

```shell
# Install uv
pip3 install --user uv
```

#### Building the project

```shell
# Build the project
uv build
```

#### Running scripts

```shell
uv run <script>
```

#### Invoking tools

```shell
# Invoke ruff check
uv run ruff check src

# Invoke ruff format
uv run ruff format src

# Invoke mypy for static checking
uv run mypy src

# Invoke pytest
uv run pytest tests
```


### Useful commands

List USB devices:
```shell
lsusb
```

View USB devices:
```shell
usbview
```

Display output from the `/dev/ttyUSB0` serial device:
```shell
screen /dev/ttyUSB0 115200
```

Dumping data from the `/dev/ttyUSB0` serial device to file:
```shell
dd if=/dev/ttyUSB0 of=usb_dump.bin bs=1M status=progress
```

Getting the process IDs for processes that use the `/dev/ttyUSB0` device:
```shell
fuser -v /dev/ttyUSB0
```


### References

1) [https://docs.astral.sh/uv/getting-started/](https://docs.astral.sh/uv/getting-started/)
