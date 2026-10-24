# 电池电量读取（可选 ADC 分压；不接时返回固定值）
import config

_adc = None
_adc_pin = None


def read_percent():
    """返回 0-100。未配置 BATTERY_ADC_PIN 时返回 BATTERY_DEFAULT。"""
    global _adc, _adc_pin
    if config.BATTERY_ADC_PIN is None:
        return config.BATTERY_DEFAULT
    try:
        import machine
        if _adc is None or _adc_pin != config.BATTERY_ADC_PIN:
            _adc = machine.ADC(machine.Pin(config.BATTERY_ADC_PIN))
            try:
                _adc.atten(machine.ADC.ATTN_11DB)
            except AttributeError:
                pass
            _adc_pin = config.BATTERY_ADC_PIN

        raw = _adc.read()                  # 0..4095
        mv = int(raw * 3300 / 4095 * config.BATTERY_DIVIDER)
        full = config.BATTERY_FULL_MV
        empty = config.BATTERY_EMPTY_MV
        if mv >= full:
            return 100
        if mv <= empty:
            return 0
        return max(0, min(100, (mv - empty) * 100 // (full - empty)))
    except Exception as e:
        print("[battery] read failed:", e)
        return config.BATTERY_DEFAULT
