# 四键蓝牙键盘配置
# 按键接法：GPIO --- 按键 --- GND（内部上拉，按下为低电平）
# 换 GPIO 或换功能只需要改这个文件，然后重新上传/重启即可。

import keycodes as K

DEVICE_NAME = "ESP32 Keypad"   # 蓝牙里显示的名字

# (GPIO, HID 键码, 修饰键掩码, 备注)
# 实际接线：K1=GPIO26, K2=GPIO25, K3=GPIO33, K4=GPIO32
# 功能顺序：K1=回车, K2=空格, K3=Esc, K4=Tab
# 常用组合键例子：
#   Ctrl+C  -> (pin, K.C, K.MOD_LCTRL, "copy")
#   Shift+Tab -> (pin, K.TAB, K.MOD_LSHIFT, "backtab")
KEYS = (
    (26, K.ENTER, 0, "K1-ENTER"),
    (25, K.SPACE, 0, "K2-SPACE"),
    (33, K.ESC, 0, "K3-ESC"),
    (32, K.TAB, 0, "K4-TAB"),
)

DEBOUNCE_MS = 25   # 消抖时间（毫秒）
POLL_MS = 10       # 按键扫描周期（毫秒）

# 连接状态指示灯：D2 蓝色 LED（多数 ESP32 DevKit 接 GPIO2，高电平点亮）
# 未连接：闪烁；已连接：常亮
LED_PIN = 2
LED_ACTIVE_LOW = False   # 如果你的板子是低电平点亮，改成 True
LED_BLINK_MS = 500       # 未连接时的闪烁半周期（毫秒）

# ---------------- 电池电量 ----------------
# 没有接电池测量时，显示/上报这个固定值（0-100）
BATTERY_DEFAULT = 100

# 电池 ADC 引脚；None = 不测量。例如接 GPIO34（需外部分压，引脚电压 ≤ 3.1V）
BATTERY_ADC_PIN = None

# 分压比 = (R1 + R2) / R2；两个 100k 分压为 2.0
BATTERY_DIVIDER = 2.0

# 电量百分比对应的电压（mV）
BATTERY_FULL_MV = 4200    # 1S 锂电池满电
BATTERY_EMPTY_MV = 3300   # 1S 锂电池截止附近

BATTERY_UPDATE_MS = 30000  # 每 30 秒读一次

