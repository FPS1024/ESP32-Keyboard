#!/usr/bin/env python3
"""Fallback uploader using the friendly REPL (no raw REPL).

Usage: python3 tools/upload_friendly.py file1.py:remote1.py ...
"""
import base64
import sys
import time

import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200


class Friendly:
    def __init__(self):
        self.s = serial.Serial(PORT, BAUD, timeout=0.2)
        self.s.reset_input_buffer()
        self.s.write(b"\x02")          # exit raw REPL if stuck there
        time.sleep(0.3)
        self.s.write(b"\r\x03\x03")    # interrupt running code
        time.sleep(0.5)
        self.s.reset_input_buffer()
        self.s.write(b"\r\n")
        time.sleep(0.3)
        print("banner:", repr(self.s.read(4096)[-120:]))

    def cmd(self, line, wait=4.0):
        self.s.reset_input_buffer()
        self.s.write(line.encode() + b"\r\n")
        end = time.time() + wait
        buf = bytearray()
        while time.time() < end:
            chunk = self.s.read(4096)
            if chunk:
                buf.extend(chunk)
                if b">>>" in buf:
                    break
            elif b">>>" in buf:
                break
        return bytes(buf)

    def put(self, local, remote):
        data = open(local, "rb").read()
        print("put %s -> %s (%d bytes)" % (local, remote, len(data)))
        out = self.cmd("f = open(%r, 'wb')" % remote)
        if b"Traceback" in out:
            raise SystemExit(out.decode(errors="replace"))
        for i in range(0, len(data), 128):
            b64 = base64.b64encode(data[i:i + 128]).decode()
            out = self.cmd(
                "import ubinascii; f.write(ubinascii.a2b_base64('%s'))" % b64)
            if b"Traceback" in out:
                raise SystemExit(out.decode(errors="replace"))
        out = self.cmd("f.close()")
        if b"Traceback" in out:
            raise SystemExit(out.decode(errors="replace"))
        print(self.cmd(
            "import os; print('SIZE', os.stat(%r)[6])" % remote
        ).decode(errors="replace").strip())

    def close(self):
        self.s.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    f = Friendly()
    try:
        for arg in sys.argv[1:]:
            local, remote = arg.split(":", 1)
            f.put(local, remote)
        print(f.cmd("import os; print(os.listdir())").decode(errors="replace"))
    finally:
        f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
