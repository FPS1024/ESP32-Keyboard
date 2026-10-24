# 基于 MicroPython ubluetooth 的 BLE HID 键盘实现
# 只依赖固件自带的 bluetooth 模块，适用于 ESP32 + MicroPython 1.17

import bluetooth
import struct
import time

_IRQ_CONNECT = 1
_IRQ_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3
_IRQ_ENCRYPTION_UPDATE = 28

_READ = bluetooth.FLAG_READ
_WRITE = bluetooth.FLAG_WRITE
_WRITE_NR = bluetooth.FLAG_WRITE_NO_RESPONSE
_NOTIFY = bluetooth.FLAG_NOTIFY

# 要求加密读取，强制主机配对/绑定（iOS 的电池小组件更认真正绑定的配件）
_READ_ENC = 0x0200

# 注意：这版 MicroPython 固件里，描述符的 flags 直接是 ATT 权限位，
# 和特征的 FLAG_* 不是同一套数值。写错会导致主机读描述符被拒（Read Not Permitted）。
_DSC_READ = 0x01
_DSC_WRITE = 0x02

# 标准键盘 Report Map（Report ID = 1）
# 8 字节输入报告：修饰键, 保留, 键码 x6
# 1 字节输出报告：LED 状态（Num/Caps/Scroll Lock 等）
_REPORT_MAP = bytes((
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x06,        # Usage (Keyboard)
    0xA1, 0x01,        # Collection (Application)
    0x85, 0x01,        #   Report ID (1)

    # 修饰键：8 个 bit
    0x05, 0x07,        #   Usage Page (Key Codes)
    0x19, 0xE0,        #   Usage Minimum (Left Control)
    0x29, 0xE7,        #   Usage Maximum (Right GUI)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x01,        #   Logical Maximum (1)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x08,        #   Report Count (8)
    0x81, 0x02,        #   Input (Data, Variable, Absolute)

    # 保留字节
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x08,        #   Report Size (8)
    0x81, 0x01,        #   Input (Constant)

    # LED 输出（5 bit + 3 bit 填充）
    0x95, 0x05,        #   Report Count (5)
    0x75, 0x01,        #   Report Size (1)
    0x05, 0x08,        #   Usage Page (LEDs)
    0x19, 0x01,        #   Usage Minimum (Num Lock)
    0x29, 0x05,        #   Usage Maximum (Kana)
    0x91, 0x02,        #   Output (Data, Variable, Absolute)
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x03,        #   Report Size (3)
    0x91, 0x01,        #   Output (Constant)

    # 6 个普通键码
    0x95, 0x06,        #   Report Count (6)
    0x75, 0x08,        #   Report Size (8)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x65,        #   Logical Maximum (101)
    0x05, 0x07,        #   Usage Page (Key Codes)
    0x19, 0x00,        #   Usage Minimum (0)
    0x29, 0x65,        #   Usage Maximum (101)
    0x81, 0x00,        #   Input (Data, Array)

    0xC0,              # End Collection
))


def _adv_payload(name, services=(0x1812, 0x180F), appearance=0x03C1):
    """组装广播数据：Flags + 服务 UUID 列表 + Appearance + 名称"""
    payload = bytearray()

    def add(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    add(0x01, b"\x06")                          # LE 通用可发现，不支持 BR/EDR
    if services:
        add(0x03, b"".join(struct.pack("<H", u) for u in services))
    if appearance is not None:
        add(0x19, struct.pack("<H", appearance))
    if name:
        add(0x09, name)                         # Complete Local Name
    return bytes(payload)


class BLEHID:
    def __init__(self, name="ESP32 Keypad", battery=100):
        self.name = name
        self.battery = max(0, min(100, int(battery)))
        self.connected = False
        self.conn_handle = None
        self._ble = bluetooth.BLE()

        # 重新初始化，方便调试时反复 Ctrl-C 再启动
        try:
            self._ble.active(False)
        except OSError:
            pass
        time.sleep_ms(150)
        self._ble.active(True)
        self._ble.config(gap_name=name)

        self._register_services()
        self._ble.irq(self._irq)
        self.advertise()

    def _register_services(self):
        hid = (
            bluetooth.UUID(0x1812),
            (
                (bluetooth.UUID(0x2A4A), _READ),                       # HID Information
                (bluetooth.UUID(0x2A4B), _READ | _READ_ENC),            # Report Map (要求配对)
                (bluetooth.UUID(0x2A4C), _WRITE | _WRITE_NR),          # HID Control Point
                (bluetooth.UUID(0x2A4D), _READ | _NOTIFY,              # Input Report
                    ((bluetooth.UUID(0x2908), _DSC_READ),)),           # Report Reference
                (bluetooth.UUID(0x2A4D), _READ | _WRITE | _WRITE_NR,   # Output Report (LED)
                    ((bluetooth.UUID(0x2908), _DSC_READ),)),
                (bluetooth.UUID(0x2A4E), _READ | _WRITE_NR),           # Protocol Mode
            ),
        )
        dis = (
            bluetooth.UUID(0x180A),
            (
                (bluetooth.UUID(0x2A29), _READ),                       # Manufacturer
                (bluetooth.UUID(0x2A24), _READ),                       # Model
                (bluetooth.UUID(0x2A50), _READ),                       # PnP ID
            ),
        )
        bas = (
            bluetooth.UUID(0x180F),                                    # Battery Service
            (
                (bluetooth.UUID(0x2A19), _READ | _NOTIFY),             # Battery Level (%)
            ),
        )

        s = self._ble.gatts_register_services((hid, dis, bas))
        (self.h_info, self.h_map, self.h_ctl, self.h_in, self.h_in_ref,
         self.h_out, self.h_out_ref, self.h_proto) = s[0]
        self.h_manu, self.h_model, self.h_pnp = s[1]
        self.h_batt = s[2][0]

        self._ble.gatts_write(self.h_info, b"\x11\x01\x00\x02")   # HID 1.11, country 0, normally connectable
        self._ble.gatts_write(self.h_map, _REPORT_MAP)
        self._ble.gatts_write(self.h_in_ref, b"\x01\x01")          # Report ID 1 / Input
        self._ble.gatts_write(self.h_out_ref, b"\x01\x02")         # Report ID 1 / Output
        self._ble.gatts_write(self.h_proto, b"\x01")               # Report Protocol
        self._ble.gatts_write(self.h_manu, b"Espressif")
        self._ble.gatts_write(self.h_model, self.name.encode())
        self._ble.gatts_write(self.h_pnp, b"\x02\xe5\x02\x01\x00\x01\x00")  # USB-IF / Espressif
        self._ble.gatts_write(self.h_in, bytes(8))
        self._ble.gatts_write(self.h_out, b"\x00")
        self._ble.gatts_write(self.h_batt, bytes([self.battery]))

    def advertise(self):
        name = self.name.encode()
        adv = _adv_payload(name)
        resp = b""
        if len(adv) > 31:
            adv = _adv_payload(None)
            resp = _adv_payload(name, services=(), appearance=None)
        try:
            self._ble.gap_advertise(100000, adv_data=adv, resp_data=resp or None)
        except OSError as e:
            print("[BLE] advertise failed:", e)

    def _irq(self, event, data):
        if event == _IRQ_CONNECT:
            self.conn_handle = data[0]
            self.connected = True
            print("[BLE] connected at", time.ticks_ms(),
                  "handle =", self.conn_handle)
        elif event == _IRQ_DISCONNECT:
            self.conn_handle = None
            self.connected = False
            print("[BLE] disconnected at", time.ticks_ms())
            self.advertise()
        elif event == _IRQ_ENCRYPTION_UPDATE:
            # (conn_handle, encrypted, authenticated, bonded, key_size)
            print("[BLE] encryption:", data)
        elif event == _IRQ_GATTS_WRITE:
            _, attr = data
            if attr == self.h_proto:
                # 主机可能切换到 Boot Protocol；两种协议的报告格式相同，直接忽略
                pass
            elif attr == self.h_out:
                led = self._ble.gatts_read(self.h_out)
                print("[BLE] LED state:", led)
        else:
            print("[BLE] event", event, data)

    def set_keys(self, keys):
        """keys: [(modifier, usage_id), ...]，最多 6 个"""
        report = bytearray(8)
        mod = 0
        for i, (m, usage) in enumerate(keys[:6]):
            mod |= m
            report[2 + i] = usage
        report[0] = mod

        self._ble.gatts_write(self.h_in, report)
        if self.connected and self.conn_handle is not None:
            try:
                self._ble.gatts_notify(self.conn_handle, self.h_in, report)
            except OSError:
                # 连接刚好断开时忽略，断开事件里会重新广播
                pass

    def set_battery(self, level):
        """更新电量 0-100；连接时通知主机（iOS/macOS 会显示这个值）。"""
        level = max(0, min(100, int(level)))
        if level == self.battery:
            return
        self.battery = level
        self._ble.gatts_write(self.h_batt, bytes([level]))
        self.notify_battery()

    def notify_battery(self):
        """主动发送一次电量通知。

        有些主机（尤其 iOS 电池小组件）需要收到 notify 才会更新显示，
        即使数值没变也值得定期发一次。
        """
        if self.connected and self.conn_handle is not None:
            try:
                self._ble.gatts_notify(self.conn_handle, self.h_batt,
                                       bytes([self.battery]))
            except OSError:
                pass

    def release_all(self):
        self.set_keys([])

    def close(self):
        try:
            self._ble.gap_advertise(None)
        except OSError:
            pass
        try:
            self._ble.active(False)
        except OSError:
            pass
        self.connected = False
        self.conn_handle = None
