# 按键扫描 + 软件消抖（内部上拉，按下为低电平）

import time
from machine import Pin


class Buttons:
    def __init__(self, keys, debounce_ms=25):
        # keys: [(gpio, usage, modifier, label), ...]
        self._items = []
        for gpio, usage, mod, label in keys:
            pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
            self._items.append((pin, usage, mod, label))

        self._debounce = debounce_ms
        now = time.ticks_ms()
        self._stable = [1] * len(self._items)     # 消抖后的电平（1=松开）
        self._raw = [1] * len(self._items)        # 上一次原始电平
        self._changed = [now] * len(self._items)  # 原始电平最近一次变化的时间

    def scan(self):
        """返回事件列表：[(usage, modifier, pressed, label), ...]"""
        events = []
        now = time.ticks_ms()

        for i, (pin, usage, mod, label) in enumerate(self._items):
            raw = pin.value()
            if raw != self._raw[i]:
                self._raw[i] = raw
                self._changed[i] = now
            elif raw != self._stable[i]:
                if time.ticks_diff(now, self._changed[i]) >= self._debounce:
                    self._stable[i] = raw
                    events.append((usage, mod, raw == 0, label))

        return events
