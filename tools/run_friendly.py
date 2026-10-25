#!/usr/bin/env python3
"""Start a blocking MicroPython command via the friendly REPL and stream output.

Usage: python3 tools/run_friendly.py [seconds] [command]
"""
import serial
import sys
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 600
    cmd = sys.argv[2] if len(sys.argv) > 2 else "import kbd; kbd.main()"
    s = serial.Serial(PORT, BAUD, timeout=0.2)
    s.reset_input_buffer()
    s.write(b"\x02")          # exit raw if needed
    time.sleep(0.2)
    s.write(b"\r\x03\x03")    # interrupt anything running
    time.sleep(0.4)
    s.reset_input_buffer()
    s.write(b"\r\n")
    time.sleep(0.2)
    s.read(4096)
    s.write(cmd.encode() + b"\r\n")
    end = time.time() + secs
    while time.time() < end:
        data = s.read(4096)
        if data:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        else:
            time.sleep(0.05)
    s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
