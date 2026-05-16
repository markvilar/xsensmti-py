# ModemManager blocks /dev/ttyUSB0

## Symptom

Opening the serial port fails with:

```
Could not open port /dev/ttyUSB0: device reports readiness to read but returned
no data (device disconnected or multiple access on port?)
```

This happens even though `lsusb` and `xsensmti scan` detect the device correctly.

## Cause

ModemManager is a Linux system service that automatically probes USB serial ports
to detect mobile broadband modems. It briefly holds the port open during probing,
causing pyserial's open call to fail with the above error.

## Fix

Create a udev rule that tells ModemManager to permanently ignore the XSens MTi
device (USB vendor ID `2639`, product ID `0017`):

**1. Write the rule:**

```bash
printf 'SUBSYSTEM=="usb", ATTRS{idVendor}=="2639", ATTRS{idProduct}=="0017", ENV{ID_MM_DEVICE_IGNORE}="1"\nSUBSYSTEM=="tty", ATTRS{idVendor}=="2639", ATTRS{idProduct}=="0017", ENV{ID_MM_DEVICE_IGNORE}="1"\n' | sudo tee /etc/udev/rules.d/99-xsens-mti.rules
```

**2. Reload udev and trigger on the device:**

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=2639
```

**3. Restart ModemManager:**

```bash
sudo systemctl restart ModemManager
```

The rule persists across reboots.
