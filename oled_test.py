# 独立 OLED 测试：显示 Hello World
# 接线：模块 SCL -> GPIO22, SDA -> GPIO21, VCC -> 3.3V, GND -> GND
import machine
import ssd1306_min

SCL_PIN = 22
SDA_PIN = 21

i2c = machine.I2C(0, scl=machine.Pin(SCL_PIN),
                  sda=machine.Pin(SDA_PIN), freq=400000)
addrs = i2c.scan()
print("I2C scan:", [hex(a) for a in addrs])

if not addrs:
    print("NO DEVICE: check SCL=GPIO22, SDA=GPIO21, VCC=3.3V, GND")
else:
    addr = 0x3C if 0x3C in addrs else addrs[0]
    oled = ssd1306_min.SSD1306_I2C(128, 64, i2c, addr)
    oled.fill(0)
    oled.text("Hello World", 0, 0)
    oled.text("ESP32 Keyboard", 0, 16)
    oled.text("SCL=22 SDA=21", 0, 32)
    oled.show()
    print("DISPLAY OK addr=0x%02X" % addr)
