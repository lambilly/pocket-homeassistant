# 硬件档案：LCDWIKI ES3C35P（3.5" ESP32-S3）

> 采集于 2026-11-07。来源：lcdwiki.com 官方 wiki「3.5inch ESP32-S3 Display」+ ESPHome dev 分支 `mipi_spi/models/lcdwiki.py`（ES3C35P 模型定义，其序列转自厂家 Arduino 例程）。
> ⚠️ 用户手上的 2.8 寸资料（1~6.png）是**同系列另一块板**（ES3C28P，ILI9341V + FT6336G），**参数不可套用到 3.5 寸**。本文件只描述 3.5 寸板。

## 整机规格

| 项目 | 参数 |
| -- | -- |
| 型号 | ES3C35P（带喇叭）／ES3C35P-NS（不带喇叭） |
| 主控 | ESP32-S3，N16R8（16MB QSPI Flash + 8MB **OPI PSRAM**） |
| 屏幕 | 3.5" IPS TFT，320×480（竖屏原生），65K 色 RGB565 |
| 显示驱动 | **ST77922**，**QSPI 四线**接口 |
| 触摸 | **ST77922 内置触摸**（不是 FT6336！），I2C 地址 **0x55** |
| 音频 | ES8311 编解码（I2C 0x18）+ FM8002E 功放（PA 使能 IO1，**低电平使能**）+ 板载 MEMS 麦克风 |
| 存储 | MicroSD（SDIO 4 位）+ 16MB Flash |
| 其他 | WS2812 RGB 指示灯、3.7V 锂电池座（TP4054 充电，最大 500mA）、Type-C（直连 S3，需 USB CDC） |
| 背光 | 6 颗白光 LED，120mA，300cd/m²，PWM 可调 |

## 引脚分配（官方 wiki）

| 设备 | 信号 | GPIO | 说明 |
| -- | -- | -- | -- |
| LCD | CS | IO10 | 片选，低有效 |
| LCD | CLK | IO12 | QSPI 时钟 |
| LCD | D0 | IO11 | QSPI 数据 0（单线模式下即 MOSI） |
| LCD | D1 | IO13 | QSPI 数据 1（单线模式下即 MISO） |
| LCD | D2 | IO14 | QSPI 数据 2 |
| LCD | D3 | IO9 | QSPI 数据 3 |
| LCD | RST | EN | **与主控复位共用，没有独立 GPIO** |
| LCD | BL | IO41 | 背光，PWM 调光 |
| 触摸 | SDA | IO38 | 与 ES8311、扩展 IIC 共用 |
| 触摸 | SCL | IO39 | 与 ES8311、扩展 IIC 共用 |
| 触摸 | RST | IO48 | 低电平复位 |
| 触摸 | INT | IO47 | 触摸时拉低 |
| RGB 灯 | DATA | IO40 | WS2812 单灯 |
| SD | CLK | IO5 | SDIO |
| SD | CMD | IO4 | SDIO |
| SD | D0~D3 | IO6 / IO7 / IO2 / IO3 | SDIO 四位 |
| 音频 | PA_EN | IO1 | **低电平使能**功放 |
| 音频 | MCLK | IO17 | I2S 主时钟 |
| 音频 | BCLK | IO18 | I2S 位时钟 |
| 音频 | DOUT | IO15 | I2S 数据输出（→ 功放） |
| 音频 | LRCK | IO21 | I2S 左右声道 |
| 音频 | DIN | IO16 | I2S 数据输入（← 麦克风，经 ES8311） |
| 按键 | BOOT | IO0 | 下载模式 |
| 按键 | RESET | EN | 主控与屏共用 |
| 电池 | ADC | IO8 | 电池电压采样 |
| 扩展 | — | IO45 / IO46 | 1.25mm 4P 座（strapping 脚，慎用） |

**没有空闲 GPIO 可用**：除 IO45/IO46 外全部被占用（IO2/3/4/5/6/7/9~14/15~18/21/38~41/47/48）。

## ESPHome 侧关键约束

1. **驱动只能用 `mipi_spi`**，不能用 `ili9xxx`：QSPI 模式没有 DC 引脚，指令/数据靠 QSPI 命令字节（0x02/0x32）区分。
2. **必须 ESP-IDF 框架 + PSRAM(octal)**：`mipi_spi` 的 QSPI 走 esp_lcd，Arduino 框架不支持。
3. `bus_mode: quad` + `spi: type: quad, clk_pin: GPIO12, data_pins: [11, 13, 14, 9]`，`cs_pin: GPIO10`，`data_rate: 40MHz`（手册上限 62.5MHz）。
4. `draw_rounding: 4`——**ST77922 要求 x 坐标 4 像素对齐，否则花屏/错列**。
5. `color_order: rgb` + `invert_colors: true`（官方示例即为 RGB order + inversion on）。若颜色反了先关 `invert_colors`；若红蓝互换改 `color_order`。
6. **不支持 swap_xy**（无行列交换）：只能原生 320×480 竖屏。要横屏只能用软件 `rotation:`（吃 CPU/内存）或干脆按竖屏设计 UI。
7. 屏复位接 EN，改刷别的固件后**必须断电重插一次**，否则可能黑屏（复位没走）。
8. ESPHome 2026.10.1 **还没有** `model: ES3C35P` 预设（在 dev 分支）。当前用 `model: CUSTOM` + 完整 `init_sequence` 复刻，见 `test/display_test.yaml`。升级到含该预设的版本后可直接换 `model: ES3C35P`。
9. **触摸已自写外部组件**：ST77922 内置触摸走 I2C 0x55、16 位寄存器地址、单点 7 字节、必须一次性读完清缓冲、轮询约 30fps。ESPHome 的 `ft63x6`/`gt911` 都不适用。**已实现** `components/st77922_touch/`，协议与校准方法见 `docs/触摸-ST77922.md`。
10. **音频**：ES8311 是带 I2C 配置的 codec，ESPHome 没有对应组件；原项目的 MAX98357A（纯 I2S 功放、无 codec）方案不能直接套。可行路径见下。

## 音频可行路径（本阶段未做）

- 路线 A（推荐先试）：绕开 ES8311，直接把 I2S 数据打进 FM8002E？**不可行**——FM8002E 是模拟输入功放，ES8311 负责 D/A。
- 路线 B：用外部组件初始化 ES8311（I2C 0x18 写寄存器：时钟、采样率 24kHz、DAC 上电），再用 `media_player`/`i2s_audio` 推数据。需要写自定义 C++ 组件。
- 路线 C：暂不用板载音频，保留原项目的提示音功能但静音，或外接 I2S 功放（但已无空闲 GPIO）。

## 与原项目（HA Monitor Display）的差异

| 项目 | 原板 | 新板 ES3C35P |
| -- | -- | -- |
| 屏接口 | SPI 四线（有 DC） | **QSPI 四线（无 DC）** |
| 屏驱动 | ST7796S | **ST77922** |
| 触摸 | FT6336U @0x38 | **ST77922 内置 @0x55** |
| 音频 | MAX98357A（纯 I2S 功放） | **ES8311 codec + FM8002E** |
| 电池检测 | INA226（I2C） | **IO8 ADC 分压**（无 INA226） |
| 指示灯 | 无 | WS2812 @IO40 |
| SD 卡 | 预留 | 板载 SDIO 四位（占 IO2~IO7） |
| 可用 GPIO | GPIO35/36/37 被 PSRAM 占，其余较多 | **仅 IO45/IO46** |
