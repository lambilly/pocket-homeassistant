# Pocket HomeAssistant

口袋式 Home Assistant 信息屏。硬件换成 **LCDWIKI ES3C35P**（ESP32-S3 N16R8 + 3.5" 320×480 QSPI 触摸屏，板载喇叭/麦克风/TF 卡/电池座），软件是 **ESPHome + LVGL**：四页数据看板、触摸 TAB 导航、熄屏省电、HA 语音播报。

本项目由 **HA Monitor Display v2.2.1** 迁移而来（发布为 **v3.0**）：UI 布局、MQTT 数据通道、熄屏逻辑全部沿用，显示驱动 / 触摸驱动 / 音频链路按新硬件重写。

## 功能一览

- **四页 + 底部四键 TAB 导航**（家居 → 网络 → 系统 → 通知）
  - 家居页：时间 / 天气 / 上证指数、服务器·网关·AP·设备在线数、居家模式、车位状态、电灯·窗帘、空调·电器、在线设备 A/B
  - 网络页：WAN IP 与连接时长、五类设备在线数、网络运行 / NAS 运行 / 风扇运行三列、四路风扇转速与温度分档着色
  - 系统页：标题栏（设备名 · 运行时长 · 电量%）、SSID / IP、设备信息（含电池电压）/ 系统负载 / 网络参数
  - 通知页：单条全屏 + 上下翻页，8 槽环形缓冲（单条正文上限 3.5 KB）
- **熄屏休眠**：超时 15~900 s 可调，触摸 / BOOT 键唤醒；收到通知可配置为自动亮屏并直跳通知页
- **亮度与配色**：背光 PWM 0~100% 可调、断电记忆；每页底色 8 档可选（HA 下拉切换，无需重启）
- **电池状态**：IO8 ADC 采样电压 → 电量百分比；标题栏按供电状态切换图标（电池 / 闪电），供电/充电状态由电压趋势推断
- **语音播报 + 语音助手**：HA 里出现 `media_player.pocket_speaker`，TTS / 提示音直接推到板载喇叭；`voice_assistant` 接 HA Assist（STT/意图/TTS 全在 HA 侧），板载麦克风采集。功放自动开关（播放前使能，结束后延迟 150 ms 关闭）
- **远程控制**：屏幕带出门（HA 连不到设备）时，仍可通过 MQTT 改开关屏 / 亮度 / 熄屏超时 / 自动休眠 / 通知亮屏

## 硬件

| 项目 | 规格 |
| -- | -- |
| 型号 | LCDWIKI ES3C35P（ESP32-S3 N16R8：16 MB Flash + 8 MB OPI PSRAM） |
| 屏幕 | 3.5" IPS，320×480 原生竖屏，RGB565，300 cd/m² / 120 mA 背光 |
| 显示驱动 | **ST77922，QSPI 四线**（无 DC 脚），`mipi_spi` + `model: CUSTOM` |
| 触摸 | ST77922 内置触摸，I2C **0x55**，5 点（自写组件 `components/st77922_touch`） |
| 音频 | ES8311 codec（I2C 0x18）+ FM8002E 功放（PA 使能 IO1，低有效）+ MEMS 麦克风 |
| 存储 | MicroSD（SDIO 4 位，未启用）+ 16 MB Flash |
| 电源 | 3.7 V 锂电池座（TP4054 充电，最大 500 mA），Type-C 直连 S3 |
| 其他 | WS2812 RGB 指示灯、BOOT 键、1.25 mm 4P 扩展口 ×3（I2C / UART / IO） |

### 引脚分配

| 设备 | 信号 | GPIO | 说明 |
| -- | -- | -- | -- |
| LCD | CS / CLK | 10 / 12 | QSPI 片选与时钟 |
| LCD | D0~D3 | 11 / 13 / 14 / 9 | QSPI 四线数据 |
| LCD | RST | EN | **与主控复位共用**，无独立 GPIO（OTA 后需双软复位，见踩坑） |
| LCD | BL | 41 | 背光 PWM（LEDC 2 kHz） |
| 触摸 | SDA / SCL | 38 / 39 | 与 ES8311、I2C 扩展口共用总线（400 kHz） |
| 触摸 | RST / INT | 48 / 47 | |
| 音频 | MCLK / BCLK / LRCK | 17 / 18 / 21 | I2S 总线 |
| 音频 | DOUT / DIN | 15 / 16 | 出声 / 麦克风采集 |
| 音频 | PA_EN | 1 | 功放使能，**低电平开** |
| 电池 | ADC | 8 | R14/R15 100K 分压，读数 ×2 还原 |
| RGB 灯 | DATA | 40 | WS2812（GRB） |
| 按键 | BOOT | 0 | 短按熄屏 / 唤醒 |
| SD 卡 | CLK / CMD / D0~D3 | 5 / 4 / 6·7·2·3 | SDIO 四位，当前未启用 |
| 扩展 | I2C / UART / IO | 38·39 / 43·44 / 45·46 | IO45/46 是 strapping 脚，上电电平会影响启动模式 |

> IO35/36/37 被 OPI PSRAM 占用；除 IO43/44（UART0，日志已改走 USB CDC，可当扩展串口）与 IO45/46 外，其余引脚都已有归属。完整档案见 `docs/硬件-ES3C35P引脚与驱动.md`。

## 快速开始

### 1. 前置条件

- ESPHome **2026.10** 或更新（`es8311`、`mixer` 扬声器组件需要此版本；2026.10.1 尚无 `model: ES3C35P` 预设，故用 `CUSTOM`）
- 框架必须是 **ESP-IDF + octal PSRAM**（`mipi_spi` 的 QSPI 走 esp_lcd，Arduino 框架不支持）
- 一个 MQTT broker（局域网 1883 即可；走外网建议 8883 + TLS）

### 2. 写 `secrets.yaml`（与主配置同目录）

```yaml
wifi_ssid: your-wifi
wifi_password: your-wifi-password
ap_password: your-fallback-ap-password
api_key: "32 字节 base64，可由 esphome 生成"
mqtt_broker: your-mqtt-broker-address
mqtt_port: 1883
mqtt_username: your-mqtt-username
mqtt_password: your-mqtt-password
web_password: your-web-password
```

### 3. 部署到 HA

设备名固定 `pocket-homeassistant`，MQTT 主题与 HA 侧包一一对应。目录结构必须保持（`packages:` 用相对路径 `!include`）：

```
/config/esphome/
├── pocket-homeassistant.yaml      主配置
├── components/st77922_touch/      自定义触摸组件（external_components 引用）
├── ui/                            页面与公共资源（6 个文件）
├── include/                       notify_store.h / notify_charset.h
├── fonts/                         NotoSansSC-SemiBold.ttf + materialdesignicons-webfont.ttf
└── secrets.yaml

/config/packages/
├── pocket_display_push.yaml           每 5 s 推送 49 槽位数据帧
├── pocket_display_control.yaml        远程控制 5 实体（MQTT）
├── pocket_display_online.yaml         在线心跳（45 s 无心跳判离线）
└── pocket_display_notify_bridge.yaml  通知桥接（屏幕 ↔ HA 通知页）
```

`ha/` 下另有两个 Lovelace 卡片（`lovelace_pocket_control_card.yaml`、`lovelace_screen_control_card.yaml`）和两个 Node-RED 子流程导出（`NR子流程-屏幕推送-pocket.json` 等），按需导入。

### 4. 编译烧录

ESPHome 里 Install：首次走 USB（板子 USB 直连 S3，需 **USB CDC**），之后可 OTA。首次编译会拉音频解码库与字体子集，耗时较长。

烧完在 HA 里重载 YAML（开发者工具 → YAML → 重新加载自动化）。设备上线后 5 s 内应收到第一帧数据。

> **换固件后如果黑屏**：屏复位接在 EN 上，OTA / 软重启拿不到硬复位，**断电重插一次**即可亮；主配置的 `init_sequence` 已加双软复位 + 120 ms 规避。

## MQTT 主题

| 主题 | 方向 | 载荷 | 说明 |
| -- | -- | -- | -- |
| `home/pocket-homeassistant` | HA → 屏 | JSON（49 槽位） | 数据帧，retain + QoS1，5 s 一推 |
| `home/pocket-homeassistant/notify` | HA → 屏 | JSON | 通知，QoS1，不 retain |
| `home/pocket-homeassistant/cmd/light` | HA → 屏 | `ON` / `OFF` | 屏开关（开=唤醒到上次亮度） |
| `home/pocket-homeassistant/cmd/bright` | HA → 屏 | `10`~`100` | 亮度百分比 |
| `home/pocket-homeassistant/cmd/sleep` | HA → 屏 | `15`~`900` | 熄屏超时（秒） |
| `home/pocket-homeassistant/cmd/autosleep` | HA → 屏 | `ON` / `OFF` | 自动休眠总开关 |
| `home/pocket-homeassistant/cmd/wake` | HA → 屏 | `ON` / `OFF` | 收到通知是否亮屏 |
| `esphome/pocket-homeassistant/state` | 屏 → HA | JSON | 状态回发（retain），HA 侧实体据此显示 |
| `esphome/pocket-homeassistant/logs` | 屏 → HA | 文本 | 日志（INFO） |

`cmd/*` 全部 retain：设备重连 / 重启会重放 HA 最后一次下发的值，**重启后以 HA 侧为准**。

## 数据流

```
HA 自动化（每 5 s，Jinja 组装 49 实体 JSON）
        │ mqtt.publish  →  home/pocket-homeassistant (retain, QoS1)
        ▼
ESP32 mqtt.on_json_message ─▶ hd_* globals ─▶ template 传感器（1 s）─▶ LVGL 四页
        ▲
        └── esphome/pocket-homeassistant/state（cmd 执行结果回发，retain）
```

- 屏幕判断 "HA 离线" 用**数据新鲜度**（>15 s 无新帧），不看 WiFi 状态
- 字段统一 `hd_*` 前缀；三态字段（-1 = HA 侧实体不存在）显示为 `--`
- 通知走独立通道：MQTT → `ns_notify` 8 槽环形缓冲 → 通知页；入库时切好折行（`include/notify_store.h`）

## 目录结构

```
pocket-homeassistant.yaml    主配置：板型 / 网络 / MQTT / 屏 / 触摸 / 音频 / 电源 / LVGL 全局
pocket-ha-screen-test.yaml   点屏测试固件（可直接放 /config/esphome 编译，只验证显示/方向/颜色/背光）
ui/                          页面与公共资源
  ui_common.yaml               字体（中文本白名单 + MDI 图标）/ 全局变量 / 时钟 / TAB 高亮
  page_dashboard.yaml          页面1 家居（6 行栅格）
  page_network.yaml            页面2 网络（4 行栅格）
  page_system.yaml             页面3 系统（标题栏 + 三列信息）
  page_notify.yaml             页面4 通知（单条全屏 + 上下翻页）
  tab_bar.yaml                 底部四键导航（四页共用同一份片段）
components/st77922_touch/    自定义触摸组件（I2C 0x55，16 位寄存器，7 字节/点，FIFO 排空）
include/                     notify_store.h 通知环形缓冲/折行/清洗 + notify_charset.h 缺字扫描结果
fonts/                       NotoSansSC-SemiBold.ttf（UI）+ materialdesignicons-webfont.ttf（图标）
sounds/                      alarm / ding / notify 三个 wav（本地音效素材，当前播报走 HA 推流）
ha/                          HA 侧资源（→ /config/packages/ 部署）
  pocket_display_push.yaml         数据推送自动化（pkha_display_push）
  pocket_display_control.yaml      远程控制 5 实体
  pocket_display_online.yaml       在线心跳桥（pkha_screen_online）
  pocket_display_notify_bridge.yaml 通知桥（pkha_notify_send / pkha_last_notify）
  lovelace_pocket_control_card.yaml 屏幕控制卡片（Lovelace）
  NR子流程-屏幕推送-pocket.json     Node-RED 推送子流程
  monitor_display_*.yaml           旧屏（HA Monitor Display）遗留包，本项目不部署
docs/                        硬件档案 / 触摸协议 / 音频方案 / 外设路线图
reference/datasheet/         ES3C35P 规格书、原理图、IO 表、官方 quickstart
test/display_test.yaml       早期点屏版本（字体路径按 test/ 目录写、未含 rotation/transform，仅作历史参考）
3.5inch_ESP32-S3_快速使用手册.pdf  厂家中文手册
CHANGELOG.md                 更新日志（旧项目线的版本记录）
```

> `secrets.yaml`、`.esphome/`、`.workbuddy/` 不入库。`test/.esphome/` 是测试固件构建缓存。

## 开发注意事项（踩过的坑）

**显示**

- `display` 段**必须显式写 `transform: disabled`**。不写时默认为"启用"，`model: CUSTOM` 会被认为支持硬件变换，LVGL 于是只写 MADCTL 的 MV 位做硬件旋转——但 ST77922 **没有 MV 位**，面板不动而 LVGL 按 480 宽写入 320 宽的屏，画面呈**斜向剪切错位**。禁用后 LVGL 走软件旋转，横屏正确。
- `draw_rounding: 4` 必须保留（ST77922 要求 x 坐标 4 像素对齐，否则花屏）；`lvgl` 段也要写同一值。
- 显示层保持原生竖屏 320×480，横装 480×320 由 `lvgl: rotation` 统一旋转（渲染 + 触摸一起转）。当前 `rotation: 270` 为 180° 翻转版（配合左手握持），正装用 `90`。
- `color_order: rgb` + `invert_colors: true`；颜色反了先关 `invert_colors`，红蓝互换改 `color_order`。

**触摸**

- 协议是 16 位寄存器地址：`0x0010` 状态、`0x0014` 数据，每点 7 字节，上电读 `0x0009` 取最大触点数。**每次必须按最大点数一次性读完排空 FIFO**，否则只能点一次。
- 组件只上报原生竖屏坐标，换轴 / 翻转交给 LVGL，`touchscreen.transform` 全部 `false`。

**UI / 字体**

- 汉字与图标都是**白名单制**：`text:` 里出现的每个字都必须在字体 `glyphs` 里，否则显示方框（或编译报 `Codepoint not found`）。图标码点必须加进 `ui_common.yaml` 的 `&mdi_glyphs`，加错块同样是方框。
- 同一个码点在同一块 `glyphs` 里不能写两次，否则报 duplicate glyphs。
- 中文字号三档 12 / 16 / 20 px（SemiBold）；20 px 图标配 label 高度至少 22，写 18 会把电池之类的图标上下压掉。
- 对齐常量没有 `CENTER_MID`，居中用 `align: center`；`left_mid` / `right_mid` / `top_mid` / `bottom_mid` 才是边对齐。
- 需要随文本长度自适应（运行时长、电量+电压）时用 `layout: {type: flex, flex_flow: row}` + `width/height: SIZE_CONTENT`，不要写死 x 坐标。
- LVGL v9 的 label 未显式给宽度时是 `SIZE_CONTENT`，依赖固定宽度的布局必须显式写 `width`。

**音频**

- 公告 / 媒体两条管线**不能用同一个 speaker**，必须用 `speaker: platform: mixer` 拆成两路虚拟 source。
- `mixer` speaker 不接受 `sample_rate`（继承 output speaker）；codec、speaker、pipeline 三处采样率必须一致（当前 16 kHz）。
- PA（IO1）低有效，`inverted: true` 统一成 "ON = 有声"；结束时延迟 150 ms 再关，避免尾音被切和 "咔" 声。

**部署**

- `packages:` 里的 HA 自动化 id 必须与旧屏包**不重名**，否则同名覆盖导致新包静默失效（`pkha_` 前缀就是为此加的）。
- 同一份 `tab_bar.yaml` 被四页各 include 一次，片段内**不能带 id**，否则重复定义编译报错。
- `esphome:` 的 `includes` 要把 `notify_store.h` 依赖的 `notify_charset.h` 一并登记。
- 只有一个 `switch:` / `sensor:` 顶层键；新增设备要并进已有段，否则 YAML duplicate key。
- `ota:` 段的空 `encryption:` 块 = "必须加密且密钥继承 `api.key`"；从旧版明文 OTA 升级过来要先 USB 刷一次。

**麦克风 / 语音助手**

- 麦克风与喇叭共用同一条 `i2s_audio` 总线，三处采样率必须一致（16 kHz）；`mic_gain` 只有 0/6/12/18/24/30/36/42 八档，板载 MEMS 麦从 24DB 起。
- **`use_microphone` 必须为 `false`**：它不是"启停麦克风"，而是 REG14 bit6 的 DMIC（PDM 数字麦）选择位。板载麦是 LMA2718B381-OA7 模拟麦，置 true 会切到 PDM 通路，ADC 全 0 → RMS 恒定 **-96.3 dBFS**。
- **I2S 总线是独占的**：`i2s_audio` 用一把互斥锁，喇叭 `try_lock()` 抢不到就每秒重试（日志 `Parent bus is busy`），麦克风采集期间一直持锁 → 两者不能同时用。配置里用 `switch.mic_monitor` 显式启停采集（默认 OFF，音乐优先），并在播放/语音助手回复前后自动让路；`sound_level` 用 `passive: true` 避免常开麦。
- **采集启停必须走 `script.mic_take` / `script.mic_give`**：麦克风用「监听槽计数」管理（`MAX_LISTENERS=16`），每次 `microphone.capture` 占 1 槽、`stop_capture` 还 1 槽，16 槽全还才真正停驱动并释放总线。重复 capture 会让麦永久占线，表现为「TTS 播过一次，之后再也放不出声」。`mic_give` 会在麦未停时补还一个槽（计数封顶 16，多还无害），属于自愈手段。
- `media_player.on_play` 只在音频真正开始播放（state → PLAYING）时才触发，总线被占时永远等不到——所以它只当兜底；TTS 靠 `on_announcement`（播报管线启动瞬间就触发），音乐靠 400ms 巡检看门狗（喇叭卡在 STARTING 就让路）。
- ESPHome 已移除 ADF 的 AEC，**播报会被自己的麦收进去**：音量压到 60% 以下，或播报期间暂停采集。
- `voice_assistant` 的 `microphone` 与 `speaker`/`media_player` 输出互斥（只能选一个输出）；STT 与 TTS 在 HA 侧 pipeline 里配，设备侧只负责采集与播放。
- 没有唤醒词时用 HA 的 `assist_satellite.start_conversation` 触发对话。

## 文档索引

- [CHANGELOG.md](CHANGELOG.md) — 版本更新日志（含旧屏 v0.9 ~ v2.2 的历史）
- `docs/硬件-ES3C35P引脚与驱动.md` — 官方引脚表、驱动约束、与原板的差异
- `docs/触摸-ST77922.md` — 触摸寄存器协议、FIFO 排空、四角标定方法
- `docs/音频-ES8311方案.md` — 音频链路、ES8311 配置、HA TTS 用法
- `docs/外设启用路线图.md` — 已启用 / 待启用外设与引脚占用清单
- `3.5inch_ESP32-S3_快速使用手册.pdf` — 厂家中文手册

## 待做

- 本地唤醒词（microWakeWord）：模型占数 MB，且与 LVGL 抢 CPU，语音助手目前靠 HA 触发
- TF 卡（SDIO 四位）：ESPHome 官方无组件，需外部组件 + framework 选项调整
- 扩展口传感器（I2C 温湿度 / 光照，UART 空气质量 / 毫米波）
- 供电状态 100% 判定：需从 TP4054 CHRG 脚飞线到 IO45、USB 5V 分压到 IO46
