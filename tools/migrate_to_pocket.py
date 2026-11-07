# -*- coding: utf-8 -*-
"""把 ha-monitor-display.yaml 迁移为 pocket-homeassistant.yaml（ES3C35P 硬件层）"""
import io, sys

SRC = "ha-monitor-display.yaml"
DST = "pocket-homeassistant.yaml"

s = io.open(SRC, encoding="utf-8").read()
orig_len = len(s)

def cut(s, start_marker, end_marker, keep_end=True):
    """删除 [start_marker, end_marker) 区间，end_marker 保留"""
    i = s.find(start_marker)
    assert i >= 0, "start not found: " + start_marker[:40]
    j = s.find(end_marker, i + len(start_marker))
    assert j >= 0, "end not found: " + end_marker[:40]
    return s[:i] + s[j:]

# ---------- 1. 头部 ----------
head_end = "# 主配置：设备 / 网络 / 硬件 / HA 实体"
i = s.find(head_end)
assert i >= 0
new_head = """# ==========================================================
# Pocket HomeAssistant v3.0（迁移版，2026-11-07）
#   自 HA Monitor Display v2.2.1 迁移 UI / MQTT / 熄屏逻辑，
#   硬件层换为 LCDWIKI ES3C35P（ESP32-S3 N16R8 + ST77922 QSPI）：
#     · 显示：mipi_spi CUSTOM，初始化序列取自官方 wiki + ESPHome dev 分支，
#       序列开头双软复位 + 120ms（屏 RESET 硬线接 EN，OTA 软重启无硬复位）
#     · 触摸：自定义组件 components/st77922_touch（I2C 0x55，换轴/反转在组件内）
#     · 背光 GPIO41 LEDC / 电池 ADC IO8(×2 分压还原) / WS2812 IO40 / BOOT 键 IO0
#   音频暂未迁移：新板是 ES8311 codec，需自定义初始化组件，后续版本接入
#   MQTT 主题独立于旧屏：
#     订阅 home/pocket-homeassistant        （HA 数据帧，5s 一推）
#          home/pocket-homeassistant/notify （通知）
#          home/pocket-homeassistant/cmd/*  （远程控制）
#     发布 esphome/pocket-homeassistant/state（状态回发，retain）
#   HA 侧配套自动化：ha/pocket_display_*.yaml
# ==========================================================
"""
s = new_head + s[i:]

# ---------- 2. 设备名 / WiFi AP ----------
s = s.replace("  name: ha-monitor-display\n", "  name: pocket-homeassistant\n")
s = s.replace("  friendly_name: HA Monitor Display\n", "  friendly_name: Pocket HomeAssistant\n")
s = s.replace("    ssid: HA Monitor Fallback\n", "    ssid: Pocket HA Fallback\n")

# ---------- 3. logger 加 USB 串口 ----------
s = s.replace("logger:\n  level: INFO\n", "logger:\n  level: INFO\n  hardware_uart: USB_SERIAL_JTAG\n")

# ---------- 4. 硬件区整体替换（spi→touchscreen 区 + 音频区一起换掉） ----------
hw_start = "# --- 屏幕硬件配置 ---"
time_marker = "# ==========================================================\n# 时间：只用 SNTP，不依赖 HA"
i = s.find(hw_start); assert i >= 0
j = s.find(time_marker, i); assert j >= 0

NEW_HW = """# ==========================================================
# 屏幕硬件配置（ES3C35P：ST77922 QSPI 屏 + 内置触摸 I2C 0x55）
# ==========================================================
external_components:
  - source:
      type: local
      path: components
    components: [st77922_touch]

spi:
  id: display_spi
  type: quad
  clk_pin: GPIO12
  data_pins:
    - GPIO11
    - GPIO13
    - GPIO14
    - GPIO9

i2c:
  id: touch_i2c
  scl: GPIO39
  sda: GPIO38
  frequency: 400kHz

output:
  - platform: ledc
    pin:
      number: GPIO41
    id: lcd_backlight_pwm
    frequency: 2000Hz

light:
  - platform: monochromatic
    id: lcd_backlight
    name: "Screen Light"
    icon: mdi:monitor
    output: lcd_backlight_pwm
    # ALWAYS_OFF：开机不自带满亮点亮，由 lvgl on_boot 按 ui_saved_brightness（默认 60%）点亮，
    # 避免开机先全亮一秒再暗下来的闪变。休眠/唤醒见 script sleep_screen / wake_screen。
    restore_mode: ALWAYS_OFF
  # 板载 WS2812 单灯（IO40）：联网/告警/低电状态指示，HA 可直接控制
  - platform: esp32_rmt_led_strip
    id: status_led
    name: "Status LED"
    pin: GPIO40
    chipset: ws2812
    num_leds: 1
    channel_colors: GRB   # WS2812 实际顺序 GRB（rgb_order 是同义旧名，已废弃）
    restore_mode: ALWAYS_OFF

display:
  - platform: mipi_spi
    id: lcd_display
    model: CUSTOM
    bus_mode: quad
    cs_pin: GPIO10
    dimensions: 320x480
    rotation: 90°            # 壳内横装：显示层软件旋转成 480x320，LVGL rotation 保持 0
    transform: disabled      # ST77922 不支持硬件行列交换（swap_xy），只能软件旋转
    data_rate: 40MHz
    draw_rounding: 4         # ST77922 要求 x 坐标 4 像素对齐，否则花屏
    color_order: rgb
    invert_colors: true
    auto_clear_enabled: false
    update_interval: never   # 渲染完全由 LVGL 驱动
    # 初始化序列取自官方 ES3C35P 例程（与 ESPHome dev 分支 ES3C35P 模型一致），
    # 开头追加双软复位+120ms：屏 RESET 硬线接主控 EN（原理图 QD1 pin15），
    # OTA/软件重启时屏得不到硬复位，mipi_spi 自带软复位只等 10ms 不够，
    # 不加这段 OTA 后必黑屏（按 RESET 才亮）。
    init_sequence:
      - [0x01]
      - delay 120ms
      - [0x01]
      - delay 120ms
      - [0xF1, 0x00]
      - [0x60, 0x00, 0x00, 0x00]
      - [0x65, 0x80]
      - [0x79, 0x06]
      - [0x7B, 0x00, 0x08, 0x08]
      - [0x80, 0x55, 0x62, 0x2F, 0x17, 0xF0, 0x52, 0x70, 0xD2, 0x52, 0x62, 0xEA]
      - [0x81, 0x26, 0x52, 0x72, 0x27]
      - [0x84, 0x92, 0x25]
      - [0x87, 0x10, 0x10, 0x58, 0x00, 0x02, 0x3A]
      - [0x88, 0x00, 0x00, 0x2C, 0x10, 0x04, 0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x06]
      - [0x89, 0x00, 0x00, 0x00]
      - [0x8A, 0x13, 0x00, 0x2C, 0x00, 0x00, 0x2C, 0x10, 0x10, 0x00, 0x3E, 0x19]
      - [0x8B, 0x15, 0xB1, 0xB1, 0x44, 0x96, 0x2C, 0x10, 0x97, 0x8E]
      - [0x8C, 0x1D, 0xB1, 0xB1, 0x44, 0x96, 0x2C, 0x10, 0x50, 0x0F, 0x01, 0xC5, 0x12, 0x09]
      - [0x8D, 0x0C]
      - [0x8E, 0x33, 0x01, 0x0C, 0x13, 0x01, 0x01]
      - [0xB3, 0x00, 0x30]
      - [0x71, 0xD0]
      - [0x66, 0x02, 0x3F]
      - [0xBE, 0x26, 0x00, 0x9D]
      - [0x70, 0x01, 0xA6, 0x11, 0x40, 0xE0, 0x00, 0x11, 0x60, 0x11, 0x00, 0x00, 0x1A]
      - [0x90, 0x04, 0x04, 0x55, 0x74, 0x00, 0x40, 0x43, 0x2D, 0x2D]
      - [0x91, 0x04, 0x04, 0x55, 0x75, 0x00, 0x40, 0x42, 0x2D, 0x2D]
      - [0x92, 0x04, 0x44, 0x55, 0xC0, 0x06, 0x00, 0x07, 0x05, 0x90, 0x2D]
      - [0x93, 0x04, 0x43, 0x11, 0x00, 0x00, 0x00, 0x00, 0x05, 0x90, 0x2D]
      - [0x94, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      - [0x95, 0x96, 0x16, 0x00, 0x00, 0xFF]
      - [0x96, 0x44, 0x53, 0x03, 0x12, 0x23, 0x24, 0x06, 0x05, 0x9A, 0x2D, 0x00, 0x44]
      - [0x97, 0x44, 0x53, 0x47, 0x56, 0x20, 0x20, 0x02, 0x01, 0x9A, 0x2D, 0x00, 0x44]
      - [0xBA, 0x55, 0x9A, 0x2D, 0x9A, 0x2D]
      - [0x9A, 0x40, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00]
      - [0x9B, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00]
      - [0x9C, 0x5C, 0x12, 0x00, 0x00, 0x10, 0x12, 0x00, 0x00, 0x10, 0x02, 0x00, 0x00, 0x00]
      - [0x9D, 0x8A, 0x51, 0x00, 0x00, 0x00, 0x80, 0x1E, 0x01]
      - [0x9E, 0x51, 0x00, 0x00, 0x00, 0x80, 0x1E, 0x01]
      - [0xB4, 0x1D, 0x1C, 0x1E, 0x0B, 0x14, 0x02, 0x13, 0x09, 0x1E, 0x00, 0x1E, 0x10]
      - [0xB5, 0x1D, 0x1C, 0x1E, 0x0A, 0x15, 0x03, 0x11, 0x08, 0x1E, 0x01, 0x1E, 0x12]
      - [0xB6, 0x77, 0x77, 0x00, 0x0A, 0xFF, 0x0A, 0xFF]
      - [0x86, 0xC6, 0x04, 0xB1, 0x02, 0x58, 0x12, 0x58, 0x0C, 0x13, 0x01, 0xA5, 0x00, 0xA5, 0xA5]
      - [0xB7, 0x07, 0x0A, 0x0E, 0x06, 0x05, 0x03, 0x2B, 0x03, 0x03, 0x42, 0x07, 0x10, 0x10, 0x2E, 0x3F, 0x0D]
      - [0xB8, 0x07, 0x0A, 0x0D, 0x05, 0x05, 0x02, 0x2B, 0x02, 0x03, 0x42, 0x06, 0x10, 0x0F, 0x2E, 0x3F, 0x0D]
      - [0xB9, 0x23, 0x23]
      - [0xBF, 0x10, 0x14, 0x14, 0x0B, 0x0B, 0x0B]
      - [0xF2, 0x00]
      - [0x73, 0x04, 0xDA, 0x12, 0x54, 0x47]
      - [0x77, 0x6B, 0x5B, 0xFD, 0xC3, 0xC5]
      - [0x7A, 0x15, 0x27]
      - [0x7B, 0x04, 0x57]
      - [0x7E, 0x01, 0x0E]
      - [0xBF, 0x36]
      - [0xE3, 0x40, 0x40]
      - [0xF0, 0x00]
      - [0xD0, 0x00]
      - [0x11]
      - delay 120ms

# ── 触摸：ST77922 内置 TDDI 触摸（自定义组件，协议见 docs/触摸-ST77922.md）──
# 芯片原生坐标是竖屏 320x480；横装映射（显示横向=原生纵向、显示纵向=320-原生横向）
# 已在组件内完成。⚠️ 下面 transform 必须全关：组件已反转，mirror_y 再开 = 反两次。
touchscreen:
  - platform: st77922_touch
    id: touch_panel
    display: lcd_display
    reset_pin: GPIO48
    update_interval: 50ms
    calibration:           # 组件上报的已是横装 480x320 坐标，这里 1:1
      x_min: 0
      x_max: 480
      y_min: 0
      y_max: 320
    transform:
      swap_xy: false
      mirror_x: false
      mirror_y: false
    on_touch:
      - lambda: id(ui_touch_active) = true;
      # 熄屏状态下任意触摸立即点亮
      - if:
          condition:
            lambda: return id(ui_screen_off);
          then:
            - script.execute: wake_screen
    on_release:
      - lambda: id(ui_touch_active) = false;

"""
s = s[:i] + NEW_HW + s[j:]

# ---------- 5. LVGL 适配 ----------
s = s.replace("  rotation: 270                     # 横屏 480x320（竖装倒置：由 90 翻 180°）",
              "  rotation: 0                       # 方向由显示层 rotation 90°（软件旋转）负责")
s = s.replace("  draw_rounding: 8", "  draw_rounding: 4   # ST77922 x 坐标 4 像素对齐")

# ---------- 6. 删功放 interval（第二个 interval 条目） ----------
amp_iv_start = "  # ----------------------------------------------------------\n  # 功放使能跟随播放状态"
i = s.find(amp_iv_start); assert i >= 0
j = s.find("debug:\n", i); assert j >= 0
s = s[:i] + s[j:]

# ---------- 7. 删 amp_sd 开关 ----------
amp_sw_start = "  # 功放使能（MAX98357A SD 脚）"
i = s.find(amp_sw_start); assert i >= 0
j = s.find("  # 自动休眠总开关", i); assert j >= 0
s = s[:i] + s[j:]

# ---------- 8. 删 amp_idle_ms 全局 ----------
amp_g_start = "  # 功放静默计时（ms）：0 = 未开始计时。"
i = s.find(amp_g_start); assert i >= 0
j = s.find("  - id: hd_ts", i); assert j >= 0
s = s[:i] + s[j:]

# ---------- 9. 电池采样（插在 uptime 传感器后） ----------
up_anchor = '  - platform: uptime\n    id: uptime_sensor\n    icon: mdi:clock-start\n    name: "Uptime"\n'
i = s.find(up_anchor); assert i >= 0
BAT = """  # ==========================================================
  # 板载电池采样（ES3C35P）：R14/R15 100K 分压进 IO8，读数 ×2 还原电池电压
  # ==========================================================
  - platform: adc
    pin: GPIO8
    id: bat_volt
    name: "Battery Voltage"
    attenuation: 12db
    update_interval: 30s
    unit_of_measurement: V
    accuracy_decimals: 2
    filters:
      - multiply: 2.0
      - median:
          window_size: 5
          send_every: 2
          send_first_at: 2
  - platform: copy
    source_id: bat_volt
    id: bat_pct
    name: "Battery Level"
    unit_of_measurement: "%"
    accuracy_decimals: 0
    filters:
      - lambda: |-
          float p = (x - 3.30f) / (4.20f - 3.30f) * 100.0f;
          return clamp(p, 0.0f, 100.0f);
"""
s = s[:i + len(up_anchor)] + BAT + s[i + len(up_anchor):]

# ---------- 10. BOOT 键（插在 binary_sensor: 列表头） ----------
bs_anchor = "binary_sensor:\n"
i = s.find(bs_anchor); assert i >= 0
BTN = """  # ==========================================================
  # BOOT 键（IO0）：短按 = 熄屏/唤醒切换（与触摸唤醒同一套脚本，状态一致）
  # ==========================================================
  - platform: gpio
    id: btn_boot
    name: "Boot Button"
    pin:
      number: GPIO0
      mode: INPUT_PULLUP
      inverted: true
    filters:
      - delayed_on: 50ms
    on_press:
      - if:
          condition:
            lambda: return id(ui_screen_off);
          then:
            - script.execute: wake_screen
          else:
            - script.execute: sleep_screen
"""
s = s[:i + len(bs_anchor)] + BTN + s[i + len(bs_anchor):]

# ---------- 11. MQTT 主题整体改名 ----------
s = s.replace("home/ha-monitor-display", "home/pocket-homeassistant")
s = s.replace("esphome/ha-monitor-display", "esphome/pocket-homeassistant")

io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
print("OK  %d -> %d chars" % (orig_len, len(s)))
