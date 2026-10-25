# ESP32 四键蓝牙键盘（MicroPython / BLE HID）

## 当前状态

- ✅ BLE HID 键盘协议（Report Map、Report Reference、LED 输出报告）
- ✅ 4 路按键扫描 + 软件消抖，按下/松开成对发送，支持多键同时按
- ✅ 支持修饰键（Ctrl/Shift/Alt/GUI）组合
- ✅ 可选连接指示灯
- ✅ 已在 Ubuntu + BlueZ 上完整实测：扫描 → 配对 → HID 枚举 → 物理按键触发
  `KEY_ENTER` / `KEY_SPACE` / `KEY_ESC` / `KEY_TAB` 的按下和松开
- ✅ 四个物理按键已实测：K1→GPIO26、K2→GPIO25、K3→GPIO33、K4→GPIO32，每键独立、无串扰
- ✅ OLED 已实测：SSD1306/SSD1315，I2C 地址 `0x3C`，SCL=GPIO22、SDA=GPIO21，可显示 Hello World
- ✅ 键盘运行时 OLED 状态屏：未连接显示 `Not connected / Please connect`，
  连接后显示 `Connected 100% / Ready`，按键时底部显示 `K1-ENTER` 等
- ✅ 屏幕采用分页/分块慢刷，实测连接和按键刷新期间 BLE **0 掉线**
- ✅ Battery Service（`0x180F` / `0x2A19`）：主机和 OLED 都能显示电量；
  默认 `BATTERY_DEFAULT=100`，接电池分压后可显示真实电量
- ✅ 广播同时带 HID `0x1812` 和电池 `0x180F`，Appearance 为键盘，便于 iOS/macOS 识别
- ✅ iPhone 实测通过：出现配对/绑定流程，负一屏电池小组件显示电量
- ✅ `main.py` 已启用，上电自动运行
- ✅ D2 蓝色状态灯：未连接闪烁，连接后常亮

## 接线

当前使用 **0.96 寸 OLED 四键模块（SSD1306/SSD1315）**：

```
模块 GND  ──  ESP32 GND
模块 VCC  ──  ESP32 3.3V      ← 必须接！模块上 K1~K4 有约 4.7k 上拉电阻
模块 K1   ──  GPIO26  （回车）
模块 K2   ──  GPIO25  （空格）
模块 K3   ──  GPIO33  （Esc）
模块 K4   ──  GPIO32  （Tab）
模块 SCL  ──  GPIO22  （OLED）
模块 SDA  ──  GPIO21  （OLED）
```

模块排针顺序通常是 `GND VCC SCL SDA K4 K3 K2 K1`（K 侧是反序）。
只当键盘用时 SCL/SDA 可以不接。

> **重要：VCC 必须接 3.3V。** 模块的 K1~K4 通过约 4.7k 上拉到 VCC；
> VCC 悬空时四个 K 脚会通过上拉电阻互相耦合，表现为“按任意一个键，
> 四个 GPIO 一起变低”。实测 K1–K2 之间约 9.2kΩ（两个 4.7k 串联），
> 就是这个问题。

换引脚只改 `config.py`。避开 GPIO6~11（接 Flash）、GPIO34~39（无内部上拉）以及启动 strapping 引脚。

## 文件

| 文件 | 作用 |
| --- | --- |
| `config.py` | 设备名、按键 GPIO/键码/修饰键、消抖时间、指示灯 |
| `keycodes.py` | 常用 HID Usage ID 和修饰键常量 |
| `ble_hid.py` | BLE HID 键盘协议实现（服务注册、广播、通知） |
| `buttons.py` | 按键扫描与消抖 |
| `kbd.py` | 键盘主循环（模块形式，方便调试） |
| `main.py` | 开机入口，上电自动运行（`import kbd; kbd.main()`） |
| `ssd1306_min.py` | 精简 SSD1306/SSD1315 I2C 驱动（分块慢刷） |
| `ui.py` | OLED 状态界面（未连接/已连接/按键/电量） |
| `battery.py` | 电池 ADC 读取（可选） |
| `oled_test.py` | 独立的 OLED Hello World 测试 |
| `tools/repl.py` | 自制的串口 raw-REPL 上传/调试工具（替代 mpremote） |
| `tools/upload_friendly.py` | raw REPL 卡住时的友好 REPL 上传备用工具 |
| `tools/run_friendly.py` | 通过友好 REPL 启动程序并串口收日志 |

## 运行

上电会自动执行 `main.py`（内容为 `import kbd; kbd.main()`），同时初始化键盘和 OLED 状态屏，不需要手动操作。

需要调试时：

- 在串口 REPL 里按 **Ctrl-C** 停住当前程序；或
- 临时把 ESP 上的 `main.py` 改名，再手动运行：

```python
import kbd
kbd.main()
```

运行 OLED 测试：

```python
exec(open('oled_test.py').read())
```

> `main.py` 只在开机时执行一次；修改 `config.py` 或任何代码后需要复位
> （Ctrl-D / `machine.reset()`）才会生效。

## 配对

Linux（BlueZ）：

```bash
bluetoothctl
power on
agent on
default-agent
scan on
pair EC:64:C9:90:8C:CE
trust EC:64:C9:90:8C:CE
connect EC:64:C9:90:8C:CE
```

Windows / macOS：在系统蓝牙设置里添加设备，选择 `ESP32 Keypad`。

## OLED 显示

- 接线：`SCL → GPIO22`、`SDA → GPIO21`、`VCC → 3.3V`、`GND → GND`
- I2C 地址：`0x3C`（用 `i2c.scan()` 可确认）
- 测试：

```python
exec(open('oled_test.py').read())
```

- 驱动在 `ssd1306_min.py`，用法：

```python
import machine, ssd1306_min
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
oled = ssd1306_min.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.text("Hello World", 0, 0)
oled.show()
```

> 这块是**单色 OLED**（每个像素只有亮/灭），不能显示彩色；彩色需要换 TFT。
>
> **GPIO34/35（以及 36~39）是输入专用脚，不能做 I2C 的 SCL/SDA。**

### 键盘状态屏

`kbd.py` 启动时会自动初始化屏幕：

- 未连接：`Not connected` / `Please connect`
- 连接后（等待约 3 秒让主机完成配对）：`Connected` / `Ready`
- 按键时底部一行更新为 `K1-ENTER` / `K2-SPACE` 等

刷新策略很重要：BLE 连接期间**不要**用整屏 `show()`。应使用
`show_slow()` / `show_pages_slow()` 分块发送，块间 `time.sleep_ms()`；
按键只更新 page 5。否则 ESP32 的 BLE 协议栈会被 I2C 突发饿死，
表现为**每刷一次屏就掉一次线**（实测整屏刷新 30 秒掉 40+ 次）。

## D2 状态灯

- D2 是单色蓝色 LED，多数 ESP32 DevKit 接 **GPIO2**，高电平点亮
- 未连接：每 `LED_BLINK_MS`（默认 500ms）闪烁
- 已连接：常亮
- 配置在 `config.py`：

```python
LED_PIN = 2
LED_ACTIVE_LOW = False
LED_BLINK_MS = 500
```

如果板子是低电平点亮，把 `LED_ACTIVE_LOW` 改成 `True`。

> **PWR 红灯**通常是硬件直连 3.3V，不是 GPIO，软件无法关闭；
> 只能拆掉 LED/限流电阻或割线。

## 电量显示与 Apple 设备

已实现标准 Battery Service：

- Service `0x180F`，Battery Level `0x2A19`（READ + NOTIFY）
- 广播同时带 HID `0x1812` 和电池 `0x180F`，Appearance 为键盘 `0x03C1`
- HID Report Map 要求加密读取（`_READ_ENC`），强制主机完成配对/绑定；
  iOS 的电池小组件更认真正绑定的配件
- 连接后主动 notify 电量，部分主机需要 notify 才会更新电量显示
- OLED 连接后显示 `Connected 100%`

### 没有电池时

`config.py` 里 `BATTERY_ADC_PIN = None`，电量固定为
`BATTERY_DEFAULT = 100`。主机和屏幕都会显示 100%。

### 接 1S 锂电池（可选）

用两个 100k 电阻分压，把电池电压降到 ADC 安全范围：

```
BAT+ ── 100k ── GPIO34 ── 100k ── GND
```

然后修改 `config.py`：

```python
BATTERY_ADC_PIN = 34
BATTERY_DIVIDER = 2.0
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300
```

GPIO34 是输入专用脚，但可以做 ADC；引脚电压不要超过约 3.1V。
只用 USB 供电、没有电池时保持 `BATTERY_ADC_PIN = None` 即可。

### iOS / macOS 配对

已在 iPhone 上实测通过：

1. 设置 → 蓝牙 → 选择 `ESP32 Keypad`；
2. 会出现配对/绑定流程，正常确认即可；
3. 连接后负一屏 / 电池小组件会显示 `ESP32 Keypad` 的电量；
4. OLED 同时从 `Not connected` 切到 `Connected 100% / Ready`。

说明：

- iOS 的 **`i` → 设备类型**菜单只针对音频配件（车载、耳机、助听器、
  扬声器），**没有键盘/手柄选项**，所以看不到是正常的；
- 电池小组件的图标目前是**通用蓝牙图标**。iOS 用 GAP 服务的 Appearance
  特征（`0x2A01`）决定图标，而当前固件无法设置它
  （`ble.config(gap_appearance=...)` 不支持，官方 MicroPython 也未合并）。
  要变成键盘图标需要自定义固件，在 NimBLE 初始化时调用
  `ble_svc_gap_device_appearance_set(0x03C1)`；不影响任何功能。
- 这版固件不保存 bond：ESP 每次复位后，iPhone 可能需要在蓝牙设置里
  忽略设备再重新配对。

## 已知限制（重要）

### 电池小组件图标

iOS/macOS 的电池小组件图标由 GAP Appearance 特征（`0x2A01`）决定。
当前固件无法设置它（`ble.config(gap_appearance=...)` 返回 unknown config
param，官方 MicroPython 也未合并），所以图标是通用蓝牙图标。
变成键盘图标需要自定义编译固件，功能本身不受影响。

### bond 不持久化

这版固件（`MicroPython v1.17-207-g97a7cc243-dirty`，NimBLE 协议栈）**不支持 bond 持久化**：

- ESP 每次掉电/复位，或代码里重新初始化 BLE 后，主机保存的配对密钥就失效；
- HID Report Map 现在要求加密读取，主机会先配对；如果主机还留着旧密钥，
  会表现为连上又立刻断开、反复重连；
- **每次给 ESP 断电重启后**都可能需要重新配对一次；
- 解决：在主机上**先断开再删除**设备，然后重新配对。Linux：

```bash
bluetoothctl disconnect EC:64:C9:90:8C:CE
bluetoothctl remove EC:64:C9:90:8C:CE
```

> `remove` 时设备如果还连着会删不掉；如果 BlueZ 报 `NotReady`/适配器
> `Powered: no`，执行 `sudo systemctl restart bluetooth` 后再试。

彻底解决需要升级到支持 bond + NVS keystore 的固件，但注意新版本
MicroPython 的描述符 flags 语义与这版相反（见下方踩坑记录）。

## 踩坑记录

1. **0x2908 Report Reference 描述符的 flags 必须用原始 ATT 权限位**
   - 这版固件：`0x01` = 可读，`0x02` = 可写；
   - 不能直接用 `bluetooth.FLAG_READ`（值为 `0x02`，会被当成“可写”）；
   - 写错时 BlueZ 读取描述符返回 `Read Not Permitted`，HOG 插件不会订阅
     输入报告，现象是“已连接、ESP 也在发通知，但系统收不到按键”。
   - 相关：MicroPython issue #15627（v1.20+ 语义反转，取值需相应调整）。

2. 广播数据里要带 HID 服务 UUID `0x1812` 和 Appearance `0x03C1`，
   否则部分主机不会把它当键盘。

3. Linux 上 HID 服务被 BlueZ 的 `hog` 插件接管，不会出现在
   `bluetoothctl` 的 GATT 列表里，这是正常现象。

4. **四键模块的 VCC 必须接 3.3V**。模块的 K1~K4 各有约 4.7k 上拉电阻到 VCC；
   VCC 悬空时四个 K 脚通过电阻网络互相耦合，现象是“按任意一个键，四个 GPIO
   一起变低”。万用表量 K1–K2 约 9.2kΩ（两个 4.7k 串联）即可确认。接上 VCC
   后四个脚立刻独立。

5. 自编译固件的 REPL 多行粘贴容易乱，`tools/repl.py` 用 raw REPL 协议
   可靠上传和运行代码：

```bash
python3 tools/repl.py ls
python3 tools/repl.py put kbd.py :kbd.py
python3 tools/repl.py exec "import kbd; print('ok')"
python3 tools/repl.py start "import kbd; kbd.main()" 60   # 跑 60 秒并实时输出
```

6. **不要用 GPIO34/35 做 I2C**。ESP32-D0WD-V3 的 GPIO34~39 是输入专用脚，
   无法驱动 SCL/SDA。屏幕应接 GPIO22（SCL）和 GPIO21（SDA）。

7. **不要往 TX0/GPIO1 或 RX0/GPIO3 接线**。这两个是串口 REPL 用的，
   接上屏幕/按键线会导致 Thonny、esptool 和 `tools/repl.py` 全部失联
   （蓝牙仍能广播，板子没坏，只是串口不通）。如果串口突然没反应：
   拔掉所有外接线、按 EN/RST 复位即可恢复。

8. 如果串口卡在 raw REPL，Thonny 的 Ctrl-C / Stop 是退不出来的，
   需要发 **Ctrl-B** 或硬件复位。主程序现在是 `main.py`，开机自动运行；
   调试时按 Ctrl-C，或临时把 `main.py` 改名。

9. **OLED 刷新会饿死 BLE**。整屏 1KB I2C 突发会让 BLE 连接立刻断开，
   30 秒内可掉 40+ 次；3 字节命令则完全稳定。当前实现：
   - `show_slow()`：16 字节一块，每块间隔 5ms；
   - `show_pages_slow()`：逐页发送，页间再等 200ms；
   - 连接后等 3 秒让主机完成配对，再刷新状态区；
   - 按键只刷新 page 5（底部一行），不动整屏。
