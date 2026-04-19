"""
Minimal script for recording data from a serial device.
"""

import argparse
import signal
import sys
import time
import serial

from pathlib import Path


running: bool = True


def stop_handler(signum, frame):
    global running
    running = False


def main():
    parser = argparse.ArgumentParser(description="Record raw serial data to a binary file")
    parser.add_argument("port", help="Serial port, e.g. /dev/ttyUSB0 or /dev/ttyACM0")
    parser.add_argument("output", help="Output binary file path")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Read timeout in seconds (default: 1.0)")
    parser.add_argument("--append", action="store_true", help="Append to output instead of overwriting")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    mode = "ab" if args.append else "wb"
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=args.timeout,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )

    total = 0
    start = time.time()

    try:
        with out_path.open(mode, buffering=0) as f:
            while running:
                chunk = ser.read(4096)
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
    finally:
        ser.close()

    elapsed = max(time.time() - start, 1e-9)
    sys.stderr.write(f"Captured {total} bytes in {elapsed:.2f} s ({total/elapsed:.1f} B/s)\n")


if __name__ == "__main__":
    main()
