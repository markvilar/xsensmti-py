# MTi device not responding to GOTOCONFIG

## Symptom

`xsens scan` reports "No MTi devices found" even though the device is visible in `lsusb`
and `/dev/ttyUSB0` exists. With `--verbose`, the log shows:

```
DEBUG | /dev/ttyUSB0: no MTi device found
```

The scanner times out waiting for `GOTOCONFIG_ACK` (2 s default).

## Environment

- Device: XSens MTi-G-700 GPS/INS (`lsusb`: `2639:0017`)
- Interface: USB via `xsens_mt` kernel driver → `/dev/ttyUSB0`
- USB endpoints: Bulk OUT ep2 (host → device), Bulk IN ep3 (device → host)

## Investigation

### Device is reachable

Raw reads confirm the device IS streaming well-formed MTDATA2 frames at ~100 Hz:

```
faff3665...  (MID=0x36, LEN=101, standard frame, 106 bytes total)
```

Writes reach the device: sending `RESET` (FA FF 40 00 C1) stops streaming
immediately, confirming the USB write path is functional.

### GOTOCONFIG is silently ignored

Sending `GOTOCONFIG` (FA FF 30 00 D1) while the device is in this state produces
no response — the device continues streaming MTDATA2 indefinitely. In 35 KB of
captured data (3 s) there is no `GOTOCONFIG_ACK` (FA FF 31 00 D0).

Variations tested that made no difference:
- Hardware flow control (`rtscts=True`, `dsrdtr=True`)
- 1 s stabilisation delay after opening the port
- Sending `WAKEUP_ACK` (FA FF 3F 00 C2) first
- Omitting `reset_input_buffer()` before sending

### RESET + retry unblocks GOTOCONFIG

Sending `RESET`, then repeatedly sending `GOTOCONFIG` every 100 ms, produces an ACK
roughly **1.7 s after the reset**:

```
t=0.00s  RESET sent → device stops streaming
t=0.20s  GOTOCONFIG attempt 1  (no response, device still booting)
...
t=1.70s  GOTOCONFIG attempt 16
t=1.81s  >>> GOTOCONFIG_ACK received: faff3100d0
```

The device accepts `GOTOCONFIG` while still streaming MTDATA2 after the reboot —
confirming the issue was not "measurement mode rejects GOTOCONFIG" but rather a
bad persistent state in the device's NVM configuration.

## Root cause

The device had a faulty NVM configuration (likely an extreme output rate or corrupted
output configuration block) that caused its command-processing loop to ignore
`GOTOCONFIG`. A hardware reset clears this and the device becomes responsive again
within ~2 s of boot.

## Recovery procedure

Run these steps once to restore the device to a known-good state.

### 1. Xbus frame reference

| Message              | MID    | Full frame (no payload) |
|----------------------|--------|-------------------------|
| RESET                | `0x40` | `FA FF 40 00 C1`        |
| GOTOCONFIG           | `0x30` | `FA FF 30 00 D1`        |
| GOTOCONFIG_ACK       | `0x31` | `FA FF 31 00 D0`        |
| RestoreFactoryDefaults | `0x0E` | `FA FF 0E 00 F3`      |
| RestoreFactoryDefaults_ACK | `0x0F` | `FA FF 0F 00 F2` |

### 2. Steps

```python
import serial, time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)

# Step 1: hardware reset
ser.write(bytes([0xFA, 0xFF, 0x40, 0x00, 0xC1]))
ser.flush()
print("RESET sent — waiting for device to reboot...")

# Step 2: send GOTOCONFIG every 100 ms until ACK (up to 5 s)
gotoconfig     = bytes([0xFA, 0xFF, 0x30, 0x00, 0xD1])
gotoconfig_ack = bytes([0xFA, 0xFF, 0x31, 0x00, 0xD0])

buf = bytearray()
deadline = time.monotonic() + 5.0
in_config = False

while time.monotonic() < deadline:
    ser.write(gotoconfig)
    ser.flush()
    t_end = time.monotonic() + 0.1
    while time.monotonic() < t_end:
        buf.extend(ser.read(256))
    if gotoconfig_ack in bytes(buf):
        print("GOTOCONFIG_ACK received — device is in config mode")
        in_config = True
        break

if not in_config:
    print("ERROR: device did not respond to GOTOCONFIG within 5 s")
    ser.close()
    raise SystemExit(1)

# Step 3: restore factory defaults
restore     = bytes([0xFA, 0xFF, 0x0E, 0x00, 0xF3])
restore_ack = bytes([0xFA, 0xFF, 0x0F, 0x00, 0xF2])

ser.reset_input_buffer()
ser.write(restore)
ser.flush()

buf = bytearray()
deadline = time.monotonic() + 3.0
while time.monotonic() < deadline:
    buf.extend(ser.read(256))
    if restore_ack in bytes(buf):
        print("Factory defaults restored — device is ready")
        break
else:
    print("WARNING: no ACK for RestoreFactoryDefaults")

ser.close()
```

### 3. Verification

After running the script, `xsens scan` should find the device normally:

```
$ uv run xsens scan
/dev/ttyUSB0  device_id=0x...  baud=115200  product=MTi-G-700
```

## Notes

- `RestoreFactoryDefaults` requires config mode; it cannot be sent while streaming.
- The RESET + retry pattern (~1.7 s boot window) is specific to the MTi-G 7xx
  series. Newer MTi 600/800-series devices may respond to `GOTOCONFIG` directly
  without a prior reset.
- The checksum for a zero-payload Xbus frame is `(-sum(BID, MID, LEN)) & 0xFF`.
