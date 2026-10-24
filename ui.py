# 128x64 OLED 状态界面（英文，framebuf 内置 8x8 字库）
#
# 注意：这版 ESP32 MicroPython 上，连续大块 I2C 写会饿死 BLE 协议栈。
# 这里只更新状态区（page 3~5），逐页慢刷；按键只刷 page 5。


class StatusUI:
    WIDTH = 128
    HEIGHT = 64

    def __init__(self, oled, name):
        self.oled = oled
        self.name = name[:16]
        self.fb = oled.fb

    def _center(self, text, y, color=1):
        x = max(0, (self.WIDTH - len(text) * 8) // 2)
        self.fb.text(text, x, y, color)

    def _draw_header(self):
        self.fb.fill(0)
        self.fb.fill_rect(0, 0, self.WIDTH, 15, 1)
        self._center(self.name, 4, 0)
        self.fb.hline(0, 16, self.WIDTH, 1)

    def _draw_status(self, line1, line2):
        # 只清 y=24..47，对应 page 3~5
        self.fb.fill_rect(0, 24, self.WIDTH, 24, 0)
        self._center(line1, 27)
        self._center(line2, 40)

    def init_screen(self):
        """开机首次绘制：画标题 + 未连接状态，整屏逐页慢刷。"""
        self._draw_header()
        self._draw_status("Not connected", "Please connect")
        self.oled.show_pages_slow(0, 7)

    def show_disconnected(self):
        self._draw_status("Not connected", "Please connect")
        self.oled.show_pages_slow(3, 5)

    def show_connected(self, key=None, battery=None):
        line1 = "Connected"
        if battery is not None:
            line1 = "Connected %d%%" % battery
        self._draw_status(line1, key if key else "Ready")
        self.oled.show_pages_slow(3, 5)

    def show_key(self, key):
        # 只更新底部一行（page 5）
        self.fb.fill_rect(0, 40, self.WIDTH, 8, 0)
        self._center(key, 40)
        self.oled.show_slow(5, 5)
