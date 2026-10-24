#!/usr/bin/env python3
"""Minimal mpremote replacement: raw-REPL exec + file put/get over pyserial.

Usage:
  python3 tools/repl.py exec "print(1+1)"
  python3 tools/repl.py exec-file some.py
  python3 tools/repl.py put local.py :remote.py
  python3 tools/repl.py get :remote.py local.py
  python3 tools/repl.py ls
  python3 tools/repl.py start "import kbd; kbd.main()" 300
      # run blocking code, keep serial open, stream output for N seconds
"""
import base64
import sys
import time
import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200


class Repl:
    def __init__(self, port=PORT):
        self.s = serial.Serial(port, BAUD, timeout=0.2)
        self.buf = bytearray()

    def _read_until(self, token, timeout=8.0):
        """Read until token appears; return bytes up to and including it.
        Anything after the token stays in self.buf for the next call."""
        end = time.time() + timeout
        while True:
            idx = self.buf.find(token)
            if idx >= 0:
                out = bytes(self.buf[:idx + len(token)])
                del self.buf[:idx + len(token)]
                return out
            if time.time() > end:
                raise TimeoutError("timeout, got: %r" % bytes(self.buf[-400:]))
            chunk = self.s.read(4096)
            if chunk:
                self.buf.extend(chunk)

    def enter_raw(self):
        self.s.reset_input_buffer()
        self.buf.clear()
        self.s.write(b"\r\x03\x03")       # interrupt any running program
        time.sleep(0.3)
        self.s.reset_input_buffer()
        self.buf.clear()
        self.s.write(b"\x01")             # Ctrl-A -> raw REPL
        self._read_until(b"raw REPL; CTRL-B to exit\r\n>", timeout=5)

    def exit_raw(self):
        self.s.write(b"\x02")             # Ctrl-B -> friendly REPL
        time.sleep(0.1)

    def exec_raw(self, code, timeout=15.0):
        """Run code in raw REPL and return (stdout, stderr)."""
        self.enter_raw()
        self.s.write(code.encode() + b"\r\x04")
        self._read_until(b"OK", timeout=5)
        out = self._read_until(b"\x04", timeout=timeout)[:-1]
        err = self._read_until(b"\x04", timeout=8)[:-1]
        self.exit_raw()
        return out, err

    def exec(self, code):
        out, err = self.exec_raw(code)
        return out.decode(errors="replace"), err.decode(errors="replace")

    def put(self, local_path, remote_path):
        remote_path = remote_path.lstrip(":")
        with open(local_path, "rb") as f:
            data = f.read()
        self.exec("f = open(%r, 'wb')" % remote_path)
        for i in range(0, len(data), 512):
            chunk = base64.b64encode(data[i:i + 512]).decode()
            out, err = self.exec(
                "import ubinascii\n"
                "f.write(ubinascii.a2b_base64(%r))" % chunk
            )
            if err.strip() and "Traceback" in err:
                raise RuntimeError(err)
        self.exec("f.close()\nimport os\nprint('SIZE', os.stat(%r)[6])" % remote_path)
        return len(data)

    def get(self, remote_path, local_path):
        remote_path = remote_path.lstrip(":")
        out, err = self.exec(
            "import ubinascii\n"
            "f = open(%r, 'rb')\n"
            "d = f.read()\n"
            "f.close()\n"
            "print(ubinascii.b2a_base64(d).decode())" % remote_path
        )
        if err.strip():
            raise RuntimeError(err)
        data = base64.b64decode(out.strip())
        with open(local_path, "wb") as f:
            f.write(data)
        return len(data)

    def ls(self):
        return self.exec("import os\nprint(os.listdir())")[0]

    def close(self):
        self.s.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    r = Repl()
    try:
        if cmd == "exec":
            out, err = r.exec(sys.argv[2])
            sys.stdout.write(out)
            if err.strip():
                sys.stderr.write("\n[stderr]\n" + err)
                return 1
        elif cmd == "exec-file":
            code = open(sys.argv[2]).read()
            out, err = r.exec(code)
            sys.stdout.write(out)
            if err.strip():
                sys.stderr.write("\n[stderr]\n" + err)
                return 1
        elif cmd == "put":
            n = r.put(sys.argv[2], sys.argv[3])
            print("put %d bytes -> %s" % (n, sys.argv[3]))
        elif cmd == "get":
            n = r.get(sys.argv[2], sys.argv[3])
            print("got %d bytes <- %s" % (n, sys.argv[2]))
        elif cmd == "ls":
            print(r.ls())
        elif cmd == "start":
            # start "<code>" [seconds] — run blocking code, keep serial open,
            # stream its output for the given duration (default 300s).
            code = sys.argv[2]
            secs = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0
            r.enter_raw()
            r.s.write(code.encode() + b"\r\x04")
            r._read_until(b"OK", timeout=5)
            if r.buf:
                sys.stdout.write(bytes(r.buf).decode(errors="replace"))
                sys.stdout.flush()
                r.buf.clear()
            end = time.time() + secs
            while time.time() < end:
                chunk = r.s.read(4096)
                if chunk:
                    sys.stdout.write(chunk.decode(errors="replace"))
                    sys.stdout.flush()
                else:
                    time.sleep(0.05)
            print("\n[start] %.0fs elapsed, closing" % secs)
        else:
            print(__doc__)
            return 1
    finally:
        r.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
