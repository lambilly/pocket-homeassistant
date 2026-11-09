# 更新日志（CHANGELOG）

> **版本线说明**：本仓库自 **v3.0** 起按 ES3C35P 硬件平台独立记账，早期 SPI 屏版本不在本仓库范围内。

## [v3.4] — 2026-11-08（音频单管线 · 语音入口 · 灯语重做）

- **修复「播过 TTS 就放不了音乐，反之亦然」**：拆掉 `speaker: platform: mixer` 双管线，改**单管线**
  （`media_player` 只写 `announcement_pipeline` → `spk_out`，`format: NONE` 全解码器）。
  根因：mixer 首次启动后把音频流参数锁死在第一路，第二路采样率不符即 `Incompatible audio streams`；
  且两条管线状态机互相卡。代价：TTS 会打断正在放的音乐
- **音量上限**：`volume_max: 75%`（板载小喇叭超过绝对 75% 破音），`volume_initial: 0.8`
  （滑块 60% ↔ 绝对 45%，改 0.8 后默认响度回到绝对 60%）
- **语音入口补齐**：新增 `button.start_conversation` / `button.stop_conversation`；
  `binary_sensor.btn_boot` 由 `on_press` 改 `on_multi_click`——**长按 ≥0.8 s 开始/结束对话**
  （熄屏时先唤醒再起麦），**短按 <0.6 s 仍是熄屏/唤醒**
- **语音三态配色重做**：原「青 → 蓝 → 绿」色相挤在色轮同一段，单灯珠下分不清。改为
  **聆听 品红 `255,0,184` 快呼吸 / 思考 黄 `255,209,0` 中呼吸 / 说话 绿 `0,224,89` 慢呼吸**，
  色相 315°/50°/145° 两两间隔 ≥95°，叠加节奏形成双重区分；红留给故障/低电，橙留给充电
- **两个调试开关转内部**：`switch.pa_en`、`switch.mic_monitor` 加 `internal: true`，
  不再暴露给 HA（`mic_monitor` 保留 `restore_mode: ALWAYS_OFF`）
- **`mic_take` 增加前置守卫**：喇叭未停就不 capture，消除「播放时麦克风每秒刷
  `Driver failed to start`」的日志风暴（`on_idle` 会再叫一次，业务不受影响）
- **移除状态机的 `set_transition_length(0)`**：调用本身就会置 transition 标志，与 effect 冲突，
  每次切灯态刷 `effect cannot be used with transition/flash` 警告
- **删除 `components/i2c/` 本地补丁**：此前怀疑官方 i2c 的 `recover_()` 调 `App.feed_wdt()`
  导致黑屏，串口埋点证实无关（真因是上一条的 `restore_mode`）。回归官方组件，减少仓库体积
- 文档：README 状态灯表补色值列与配色理由；音频章节改为单管线；目录结构与文档索引同步
- **设备标识彻底切割旧项目**：MQTT 远程控制包与通知桥接包的 `device.identifiers`
  由 `ha_monitor_display_remote` 改为 `pkha_remote`，设备名由「PKHA Remote」改为
  **「Pocket HA Remote」**；同机的旧项目设备则是「HA Monitor Remote」，两台不再合并。
  改名后 HA 会新生成一条「Pocket HA Remote」设备记录，旧记录变成无实体的残留，手动删一次即可
- **entity_id 与设备名解耦说明**：MQTT YAML 手动配置不支持 `object_id`（discovery 专用
  字段，写了会报 invalid config，已回退）；entity_id 由设备名+实体名生成，全新安装为
  `number.pocket_ha_remote_brightness` 这类；本机已注册实体保留旧 id，卡片无需改动
- **新增 `tools/pocket-display-generator.html` 配置生成器**（自旧项目移植，去 HA 化改名）：
  浏览器填 WiFi/MQTT、可选拉取 HA 实体列表，生成 `secrets.yaml` 片段与
  `pocket_display_push.yaml`（51 槽位），右侧 480×320 屏幕版面实时模拟与槽位联动

## [v3.3] — 2026-11-08（状态灯：WS2812 一灯多态）

- `light.status_led`（WS2812 @IO40）从「一个手动可调灯」升级为**状态指示灯**：
  新增 5 个特效（三档呼吸 `led_breathe_slow/mid/fast` + 红快闪 / 红慢闪）
- 新增 `interval: 250ms` 状态机，按优先级择一显示，只在**灯态变化**时下发一次 light call：
  出错红闪(3 s) > 聆听(青·快呼吸) > 思考(蓝) > 说话(绿) > 充电(橙) > 低电<15%(红·慢闪)
  > 未连 WiFi(白·快呼吸) > API+MQTT 全断(紫·慢呼吸) > 未读通知(琥珀)
  > Mic Monitor(冷白常亮) > 熄屏(灭) > 常态在线(暗青·极慢呼吸)
- `voice_assistant` 钩子同步灯态：`on_start`/`on_listening`→聆听、`on_stt_end`→思考、
  `on_tts_start`→说话、`on_tts_end`/`on_end`→空闲、`on_error`→红闪 3 s
- 新增 `switch.status_led_auto`（默认 ON）：关掉后巡检直接 return，灯交回 HA 手动控制，
  重新打开时强制刷新当前灯态
- 新增 globals `led_state` / `led_va` / `led_err_until`
- 实现要点：pulse 只做亮度呼吸、颜色由 `set_red/green/blue` 给，故 6 种颜色复用 3 个呼吸档；
  特效内部 `set_publish(false)`，不会逐帧刷 HA/MQTT
- 文档：README 增「状态灯语义」表；`docs/外设启用路线图.md` 同步
- 踩坑：lambda 块内的行内注释只能用 `//`，用 `#` 会被原样带进 C++ 报
  `invalid preprocessing directive`
- 提交：`bdc7792`

## [v3.2] — 2026-11-08（麦克风 · 语音助手 · I2S 时分复用）

- 启用板载模拟麦克风与 HA 语音助手：`microphone: mic_in`（I2S DIN=IO16，16 kHz/16 bit/左声道）、
  `sensor: sound_level`（`passive: true`，RMS 验证通路）、`voice_assistant` 接
  `media_player.pocket_media`（STT/意图/TTS 全在 HA 侧）。提交 `ac1f10c`
- **修复 MIC 恒为 −96.3 dBFS**：ESPHome 的 `use_microphone: true` 实为 ES8311 REG14 bit6
  的 DMIC（PDM 数字麦）选择位，本板 LMA2718B381-OA7 是**模拟麦** → 必须 `false` 走
  MIC1P/MIC1N 模拟通路。提交 `ea088b2`
- **I2S 总线时分复用**：`i2s_audio` 只有一条总线且喇叭 `try_lock()` 抢不到就每秒重试
  （`Parent bus is busy`）。新增 `switch.mic_monitor` 显式启停采集，默认 OFF（音乐优先）；
  `sound_level` 改 `passive` 不再常开麦；播放与语音助手回复前后自动让路/恢复。提交 `575548f`
- **修复「TTS 播过一次后再也放不出声」**：麦克风用监听槽计数启停（`MAX_LISTENERS=16`，
  16 槽全还才停驱动并 unlock 总线），旧写法 `on_idle` 与 VA `on_end` 各 capture 一次导致
  多占槽 → 麦永久占线。改为 `script.mic_take` / `mic_give` 统一管理（去重 + 补还自愈），
  并加 400 ms 巡检看门狗（喇叭卡在 STARTING 就让路）。提交 `1c5faa9`
- **消除起播/切换爆音**：PA 改由 100 ms 巡检在「喇叭驱动 RUNNING 后 80 ms」再打开，
  避开 ES8311 DAC 偏置与耦合电容建立造成的阶跃。提交 `f0c6c12`
- 文档：`docs/音频-ES8311方案.md` 增「麦克风与语音助手」「I2S 总线独占」两章；
  README 同步总线仲裁说明

## [v3.1] — 2026-11-07（音频输出：ES8311 → FM8002E → 喇叭）

- 方案调研：ESPHome 自带 `es8311` 组件，无需自写 C++；新增 `docs/音频-ES8311方案.md`。提交 `ddbb438`
- 第一轮落地：`audio_dac: es8311` + `i2s_audio`（MCLK17/BCLK18/LRCK21/DOUT15）+ `speaker` +
  `mixer` 双管线（announcement=WAV / media=NONE）+ `media_player.pocket_speaker`；
  PA（IO1，低有效，`inverted: true`）随播放自动开关。提交 `13e5ad9`
- PA 开关改为 HA 可见（`entity_category: diagnostic`），方便排查底噪。提交 `2739e53`

## [v3.0] — 2026-11-07（迁移到 LCDWIKI ES3C35P）

**硬件层**

- 显示：`mipi_spi` + `model: CUSTOM` 驱动 ST77922 QSPI（320×480 原生竖屏），
  初始化序列双软复位 + 120 ms（屏 RESET 接 EN，OTA 软重启无硬复位）。提交 `d347978`
- **修复画面斜向剪切**：CUSTOM 模型默认被判定支持硬件变换，而 ST77922 无 MV 位 →
  显式 `transform: disabled`，逼 LVGL 走软件旋转。提交 `8e10f8b`
- 触摸：自写组件 `components/st77922_touch`（I2C 0x55，16 位寄存器，7 字节/点，FIFO 排空）；
  坐标换轴 + 纵向反转移入组件，四角实测验证通过。提交 `323cfc4` → `04b2c49`
- 背光 LEDC（IO41）、WS2812（IO40）、电池 ADC（IO8）、BOOT 键（IO0）、I2C 总线（38/39）
- 关闭 BLE 代理（曾导致 WiFi 饥饿）；`rgb_order` 改 `channel_colors` 新写法。提交 `8e6108f`

**应用层**

- LVGL 四页 UI（家居 / 网络 / 系统 / 通知）+ 底部四键 TAB，沿用既有页面设计并改横装
- 屏 180° 翻转（`lvgl: rotation: 270`，左手持机不挡屏）；系统页标题栏三段式
  （运行时长居中、电量右对齐），电压移入「设备信息」并按供电状态换图标。
  提交 `eab04c7`、`8f27374`、`d844a21`、`3498d1d`
- 供电状态推断：无 VBUS/CHRG 检测脚，用 30 s 采样电压的跃变与 3 分钟趋势判
  「电池 / 充电中 / 外接满电」。提交 `eab04c7`
- MQTT 数据 / 通知 / 远程控制三通道；HA 包 id 统一 `pkha_` 前缀，避免与 HA 中其它包的 id
  同名导致静默失效
- **修复 MQTT 不推送**：`pocket_display_push.yaml` 的 automation id 与 HA 中另一个包同名冲突
  → 统一改 `pkha_display_push`。提交 `0780142`
- **修复电池图标显示为方框**：`\U000F0079`（mdi:battery）误加到中文通知字体块，
  补进 `&mdi_glyphs`。提交 `1c6764e`
- 目录清理：移除迁移前的旧配置副本、迁移脚本、参考案例与硬件照片、官方例程包、
  调试照片与测试构建缓存（提交 `e9cf63b`、`f7b0bf7`）；本次再删旧版 Lovelace 卡片与旧版 Node-RED 子流程
- README 按现状全量重写（硬件表 / 引脚表 / MQTT 主题表 / 目录结构 / 踩坑清单）。提交 `3178bf2`
