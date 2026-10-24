# 四键 BLE 键盘主程序（含 OLED 状态显示）
# 手动运行：  import kbd; kbd.main()
# 上电自动运行需要把 main_off.py 改回 main.py（不调试时再用）

import time

import config
import battery as battery_mod
from ble_hid import BLEHID
from buttons import Buttons


def _init_screen():
    """初始化 OLED；没有屏幕或接线不对时返回 None，不影响键盘。"""
    try:
        import machine
        import ssd1306_min
        import ui

        i2c = machine.I2C(0, scl=machine.Pin(22),
                          sda=machine.Pin(21), freq=400000)
        addrs = i2c.scan()
        if not addrs:
            print("[oled] no device")
            return None
        addr = 0x3C if 0x3C in addrs else addrs[0]
        oled = ssd1306_min.SSD1306_I2C(128, 64, i2c, addr)
        screen = ui.StatusUI(oled, config.DEVICE_NAME)
        print("[oled] ready at 0x%02X" % addr)
        return screen
    except Exception as e:
        print("[oled] init failed:", e)
        return None


def _screen_call(screen, method, *args):
    if screen is None:
        return
    try:
        getattr(screen, method)(*args)
    except Exception as e:
        print("[oled] update failed:", e)


def main():
    battery = battery_mod.read_percent()
    hid = BLEHID(config.DEVICE_NAME, battery=battery)
    buttons = Buttons(config.KEYS, config.DEBOUNCE_MS)
    screen = _init_screen()
    _screen_call(screen, "init_screen")
    next_battery = time.ticks_add(time.ticks_ms(), config.BATTERY_UPDATE_MS)

    led = None
    led_state = None
    if config.LED_PIN is not None:
        from machine import Pin
        led = Pin(config.LED_PIN, Pin.OUT, value=1)

    pressed = []   # [(usage, modifier, label), ...]
    last_connected = False
    last_key = None
    screen_ready = False
    connected_at = 0
    print("[kbd] ready:", config.DEVICE_NAME)
    print("[kbd] keys:", [(k[0], k[3]) for k in config.KEYS])

    while True:
        for usage, mod, is_down, label in buttons.scan():
            if is_down:
                if (usage, mod) not in [(u, m) for u, m, _ in pressed]:
                    pressed.append((usage, mod, label))
                last_key = label
                print("[key] down:", label)
            else:
                pressed = [p for p in pressed if not (p[0] == usage and p[1] == mod)]
                print("[key] up:  ", label)

            hid.set_keys([(m, u) for u, m, _ in pressed])

            # 先发 BLE 报告，再刷新屏幕，避免显示拖慢按键
            if is_down and screen_ready:
                _screen_call(screen, "show_key", label)

        if hid.connected != last_connected:
            last_connected = hid.connected
            if last_connected:
                # 刚连上时主机还在配对/服务发现，先等 3 秒再刷屏
                connected_at = time.ticks_ms()
                screen_ready = False
            else:
                last_key = None
                screen_ready = False
                _screen_call(screen, "show_disconnected")

        if last_connected and not screen_ready:
            if time.ticks_diff(time.ticks_ms(), connected_at) >= 3000:
                _screen_call(screen, "show_connected", last_key, battery)
                screen_ready = True
                hid.notify_battery()

        if time.ticks_diff(time.ticks_ms(), next_battery) >= 0:
            next_battery = time.ticks_add(
                time.ticks_ms(), config.BATTERY_UPDATE_MS)
            new_level = battery_mod.read_percent()
            if new_level != battery:
                battery = new_level
                hid.set_battery(battery)
                if screen_ready:
                    _screen_call(screen, "show_connected", last_key, battery)
            else:
                # 数值没变也通知一次，部分主机需要 notify 才更新电量显示
                hid.notify_battery()

        if led is not None:
            want = 0 if hid.connected else 1
            if want != led_state:
                led.value(want)
                led_state = want

        time.sleep_ms(config.POLL_MS)


if __name__ == "__main__":
    main()
