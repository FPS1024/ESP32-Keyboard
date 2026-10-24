# 精简 SSD1306 / SSD1315 I2C 驱动（128x64，基于 framebuf）
import framebuf
import time


class SSD1306_I2C:
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        self.fb = framebuf.FrameBuffer(
            self.buffer, width, height, framebuf.MONO_VLSB)
        self._init()

    def _cmd(self, *args):
        self.i2c.writeto(self.addr, bytes([0x00] + list(args)))

    def _init(self):
        self._cmd(0xAE)              # display off
        self._cmd(0xD5, 0x80)        # clock divide
        self._cmd(0xA8, self.height - 1)  # multiplex
        self._cmd(0xD3, 0x00)        # display offset
        self._cmd(0x40)              # start line 0
        self._cmd(0x8D, 0x14)        # charge pump on (3.3V)
        self._cmd(0x20, 0x00)        # horizontal addressing
        self._cmd(0xA1)              # segment remap
        self._cmd(0xC8)              # COM scan direction
        self._cmd(0xDA, 0x12)        # COM pins for 128x64
        self._cmd(0x81, 0xCF)        # contrast
        self._cmd(0xD9, 0xF1)        # precharge
        self._cmd(0xDB, 0x40)        # VCOMH
        self._cmd(0xA4)              # display follows RAM
        self._cmd(0xA6)              # normal (not inverted)
        self._cmd(0x2E)              # scroll off
        self.fill(0)
        self._cmd(0xAF)              # display on

    def fill(self, color):
        self.fb.fill(color)

    def pixel(self, x, y, color=1):
        self.fb.pixel(x, y, color)

    def text(self, string, x, y, color=1):
        self.fb.text(string, x, y, color)

    def show(self):
        """快速刷新整屏（BLE 未连接时用，或在诊断脚本里用）。"""
        self._cmd(0x21, 0x00, self.width - 1)   # column range
        self._cmd(0x22, 0x00, self.pages - 1)   # page range
        buf = self.buffer
        for i in range(0, len(buf), 32):
            self.i2c.writeto(self.addr, b"\x40" + buf[i:i + 32])

    def show_slow(self, start_page=0, end_page=None,
                  chunk=16, delay_ms=5):
        """分块慢刷，块间让出 CPU。

        ESP32 + 这版 MicroPython 上，连续大块 I2C 写会饿死 BLE 协议栈，
        导致每次屏幕刷新都掉线；拆成小块并 sleep 后链路稳定。
        """
        if end_page is None:
            end_page = self.pages - 1
        self._cmd(0x21, 0x00, self.width - 1)
        time.sleep_ms(4)
        self._cmd(0x22, start_page, end_page)
        time.sleep_ms(4)
        start = start_page * self.width
        end = (end_page + 1) * self.width
        buf = self.buffer[start:end]
        for i in range(0, len(buf), chunk):
            self.i2c.writeto(self.addr, b"\x40" + buf[i:i + chunk])
            time.sleep_ms(delay_ms)

    def show_pages_slow(self, start_page, end_page,
                        chunk=16, delay_ms=5, page_gap_ms=200):
        """逐页慢刷，页与页之间再留出时间给 BLE。"""
        for page in range(start_page, end_page + 1):
            self.show_slow(page, page, chunk, delay_ms)
            time.sleep_ms(page_gap_ms)
