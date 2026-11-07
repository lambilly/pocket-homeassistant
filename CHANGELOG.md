# 更新日志（CHANGELOG）

版本命名规则：

- **MQTT 线**：`HA Monitor Display Mqtt vX.Y.Z`（数据全部由 HA 经 MQTT 推送）
- **API 线**：`HA Monitor Display API v0.9.0`（ESPHome Native API 拉取，前身版本）
- **通知线**：`HA Monitor Display Notify v2.0`（开发中）

## [未发布] — 2026-11-04（远程控制实体英文化）

- MQTT 远程控制 5 实体改英文名（HMD 前缀）：HMD Screen Power / HMD Brightness /
  HMD Sleep Timeout / HMD Auto Sleep / HMD Notify Wake，entity_id 随之生成干净值
  （如 `number.hmd_brightness`）；**unique_id 不变**（hmd_remote_*），HA 里已有自定义不丢
- 保持挂在 MQTT 集成独立设备「HA Monitor Display 远程控制」下——外网通道单独一台设备
  是清晰边界，不与 ESPHome 设备合并
- **去掉 4 个实体的 `entity_category: config`**（亮度/熄屏超时/自动休眠/通知亮屏），
  不再被折叠进「配置」区、不再被自动仪表盘与语音助手隐藏
- 设备名统一为 **HMD Remote**，实体名去掉冗余 HMD 前缀（Screen Power / Brightness /
  Sleep Timeout / Auto Sleep / Notify Wake）——HA 会把设备名并进 entity_id，
  得到 `number.hmd_remote_brightness` 这类干净结果
- README 远程控制对照表同步更新
- 已部署 `W://packages//monitor_display_control.yaml`（md5 9f6e3b7d… 双端一致；
  旧版备份 `.workbuddy/prod-backup-20261104-0834/` 与 `-0841/`）
- **2026-11-04 实测通过（设备在外网、HA 连不到设备 6053 的真实场景）**：
  远程改亮度生效、远程改熄屏超时后按新值熄屏、远程关屏/唤醒均正常，状态回读同步
  → 确认「命令下发 + 设备执行 + retain 回读」三环全通，v2.1 远程通道达成设计目标

## [未发布] — 2026-11-04（v3.3：通知亮屏直跳通知页）

- 关屏状态下收到通知：由「只唤醒背光、停在原页面」改为 **先切 `notify_page` 再唤醒**
  （`wake_screen` 的 15s 保持不变），用户抬眼就能看到通知内容，不必再摸一下 TAB
- 条件加 `lvgl_ready` 守卫（开机瞬间的 retain 通知不会在 LVGL 未就绪时切页）；
  屏亮着时不抢当前页面（避免正看家居页被顶走）
- `notify_page` 的 `on_load` 自动置 `ui_current_page=4` 并清未读，TAB 高亮由既有 200ms 巡检同步
- 实现要点：`lvgl.page.show` 必须走动作队列，不能在 MQTT 回调的 lambda 里直接 `lv_scr_load`

## [未发布] — 2026-11-04（并入 IP5406 电源板子项目）

- 原独立目录 `D:\IP5406电源模块` 整体并入主项目 **`IP5406/`**（69 个文件，md5 逐个校验无损，
  旧目录已删除；后续电源升级事项统一在本仓库研究）
- 入库 51 个文件：KiCad 工程（`gen_kicad.py` 为单一事实来源）+ Gerber 送板包 + BOM +
  设计方案 / 采购下单指引 / 项目交接
- `.gitignore`：新增 `!IP5406/KiCad/*_Gerber_JLC.zip` 例外（根规则 `*.zip` 会误伤送板包）；
  `IP5406/.gitignore` 忽略 KiCad `.history/`、`*.bak`、`*.kicad_prl`
- `IP5406/项目交接.md` 路径引用更新为 `D:\HA Monitor Display\IP5406`；README 目录结构补 `IP5406/`

## [未发布] — 2026-11-04（生成器移动端适配）

- `tools/monitor-display-generator.html` 兼顾手机显示布局，四项改动：
  ① `≤720px` 槽位行「键名/输入框」由左右两列改上下堆叠，输入框加大触控热区；
  ② 「使用前必读」4 列表格包进 `.tbl-wrap` 横向滚动容器（窄屏不再挤压爆版，`min-width:620px`）；
  ③ 屏幕模拟图格内字号改 container query 跟随容器缩放（`.screen` 已有 `container-type:inline-size`，
     ≤400px 时标签 10px / 值 9px / TAB 12px / 备注 9px），手机 ~350px 宽不再挤出版；
  ④ `.card h2` 改 flex 布局（顺带修复了标题右侧「已填 x/51」「清空/载入示例」按钮的
     `margin-left:auto` 此前不生效、不右对齐的问题）
- 回归：生成输出与 `ha/monitor_display_push.yaml` SLOT 字典 51/51 键零差异；HTML 标签配平通过
- 桌面端布局不受影响（改动全部收在 ≤720px 断点与容器查询内，仅 h2 flex 全局生效）
- **修复（同日）**：首版把移动端媒体查询块插在样式表中段，`.slot`/`button`/`.out pre` 的
  覆盖被后面（101/90/116 行）的同权重基础规则按源顺序顶掉，手机端实际未生效——
  用户实测"还是太宽"暴露。已整块移至 `</style>` 前并补 `.grid{1fr}`（防 minmax(300px) 溢出）。
  **教训：响应式覆盖块必须放所有基础规则之后，CSS 同权重按源顺序取胜**

## [未发布] — 2026-11-03（OTA 显式加密，消除 Dashboard「需要加密OTA」提示）

- `ota:` 使用**空的 `encryption:` 块（bare block）**：编译时自动继承 `api:` 的 `api_key`
  （见 ESPHome `components/esphome/ota/_resolve_encryption_key`），明文 OTA 上传被拒绝，
  且 Dashboard 不会判定为「另外配了一把密钥」——两条安全提示都不会再出现
- 试过的两种写法及结果：省略 `encryption` → 提示「请添加加密选项以拒绝明文」；
  写 `encryption: key: !secret api_key` → 提示「还拥有自己的加密密钥，建议移除」；
  **空 `encryption:` → 无提示**，且行为等价（同样拒绝明文）
- 编译提示：`web_server` 的 `/update` 端点（浏览器直传 bin）不走加密，属局域网调试通道，
  警告可忽略；介意的话可在 `web_server:` 里禁用其 OTA
- 升级路径：当前固件 OTA 兼容明文+加密，**本次可直接无线推送**，无需线刷；
  烧录后固件只接受加密 OTA（Dashboard 会自动用 api_key 加密推送）

## [未发布] — 2026-11-03（修复：通知唤醒后屏幕闪一下就熄）

**现象**：打开「通知亮屏」（Notify Wake Screen）后，来通知时屏幕亮一下就立刻熄灭，
根本看不清通知内容。

**根因**：熄屏巡检（`ui/ui_common.yaml`，每秒一次）判断依据是 LVGL 的「无输入时间」
`lv_disp_get_inactive_time()`，而**亮屏本身不是输入事件**——通知唤醒时这个值往往
早已超过熄屏阈值（默认 60s），于是下一秒巡检就判定"该睡了"，把刚点亮的背光关掉。

**修复**：新增 `ui_hold_until`（millis 截止时刻），`wake_screen` 里写入
`now + 15s`（熄屏超时更短时按更短的来），巡检在保持期内直接跳过。
所有唤醒入口（通知、`cmd/light`、`cmd/wake`、面板开关）统一受益——此前从 HA
点亮屏幕同样会立刻被巡检关掉。

### 行为

- 来通知 → 亮屏并保持 **15 秒**（期间无触摸）→ 自动熄屏
- 期间触摸屏幕会继续按正常规则计时，不会被打断
- 保持时长是常量 `hold = 15000`（`wake_screen` 内），要改成别的秒数直接改这一处

### 验证

- `esphome config`：Configuration is valid（exit 0），生成代码含 `ui_hold_until`
  判断与 `hold = 15000`
- `millis()` 在本项目已有多处使用（`ha_data_last_ms`、通知页滚动暂停），编译风险低

## [未发布] — 2026-11-03（生成器可用性修正）

### Fixed（配置生成器 `tools/monitor-display-generator.html`）

- **槽位值统一加双引号**：此前只有文本槽位加引号，实体类槽位裸写；若填入的值含
  ` #`（空格+井号）或 `: `（冒号+空格），YAML 会把后半截当注释/映射丢掉，生成文件
  静默失效。现在所有非空值一律转义加引号（换行转空格），带引号与裸值在 YAML 中等价
- 基础配置卡改为**固定两列对齐**（此前自适应流式排布，标签换行会导致左右输入框错位），
  窄屏 <720px 自动回落单列；`API 密钥` 独占整行，说明段落横跨两列
- 「清空全部 49 个槽位」文案改为按实际数量动态计算（现为 51）
- 使用前必读开头重写：以「本页面」为主语，按「是什么 → 为什么不用改固件 → 怎么用」分段；
  并纠正屏幕类型描述（3.5 寸彩色触摸屏，非电子墨水屏）

### 验证

- 生成器输出的推送包与 `ha/monitor_display_push.yaml` 逐键比对：51/51 键、值 0 差异，
  automation 其余字段（id / mode / triggers / actions）完全一致
- 模拟图与槽位双向覆盖：第 1 页 25 键（23 格，含 2 个双键格）、第 2 页 26 键，
  无「画了但没槽位」或「有槽位但没画」
- 特殊字符用例（`车机 #1: "客厅"`、超长实体 ID、含 `#tag` 的文本）解析后均完整保留
- `secrets.yaml` 9 项与固件 `!secret` 引用完全对应（`esphome config` 校验通过）

## [未发布] — 2026-11-03（v3.1 概览页在线设备两格通用化）

**背景**：概览页右列上下两格的设备名原先写死为 `Nova13` / `Nova12`——不止屏幕文字，
连 JSON 键名（`nova13`/`nova12`）、固件全局变量（`hd_nova13`/`hd_nova12`）、模板实体
（`ha_nova13`/`ha_nova12`）都带着具体产品名，别人拿去用只能显示这两台设备。
本版把这两格彻底通用化：**名称不再固化在固件里，改由 HA 下发**。

### Changed

- JSON 键名：`nova13` / `nova12` → `device_a_online` / `device_b_online`
  （固件 `hd_device_a_online` / `hd_device_b_online`、模板实体
  `ha_device_a_online` / `ha_device_b_online` 同步改名）
- 屏幕两格：图标（固定色）+ **名称（HA 下发，可改）** + 状态（在线绿 / 离线灰），
  **三者排在同一行**（与原版观感一致，不做上下换行）；名称区宽 58px，超出自动截断
  （`long_mode: DOT`），状态固定在 x=88 不会被长名字挤走
- 名称为空时回退到「Nova13 / Nova12」（保留原有观感，仍可由 HA 覆盖）

### Added

- 新增两个**文本槽位** `device_a_name` / `device_b_name`：填纯文本（不是 entity_id），
  由推送包原样带到屏幕。槽位总数 49 → **51**

### 升级注意

- **需要重新编译烧录**（固件改了 JSON 键名与标签），同时替换
  `monitor_display_push.yaml`；两者都换完屏幕两格才恢复显示
- 只换固件不换推送包：两格显示 `--` + 默认名「Nova13/Nova12」，**不影响其他 47 个槽位**

### Changed（OTA 安全）

- `ota:` 去掉明文 `password`，也不再单独设 `encryption`：ESPHome 2026.10.1 强制 OTA 与 API
  的加密密钥一致，省略后自动复用 `api:` 的 `api_key`，不再浪费 Flash/RAM，也消掉编译警告
- `secrets.yaml` 去掉 `ota_password`（不再被引用，可保留，无副作用）

### Added（MQTT 端口可配）

- `mqtt:` 的 `port` 从写死 `1883` 改为 `!secret mqtt_port`，`secrets.yaml` 新增 `mqtt_port`
  （默认 1883）。生成器配置页同步增加「MQTT 端口」输入框，输出时按**裸数字**写入，不加引号
- TLS 8883 仍暂不支持（需额外证书与 `ssl` 配置），端口值留作后续扩展

> ⚠️ **升级注意**：从 `password` 切到加密密钥后，旧固件无法再用无线 OTA 连上，
> 必须 **USB 线刷一次**；之后恢复无线 OTA，密码为 `api_key`。

### 验证

- `esphome config`：Configuration is valid（含 `long_mode: DOT`、标签 `width`；OTA 无警告）
- `esphome compile`：编译通过，可直接线刷
- 推送包：YAML 解析 51 槽 / 渲染 56 键；jinja2 编译 + 双阶段渲染（无 SLOT 兜底 / 带 SLOT）
  均为合法 JSON，中文名称正确转义
- 生成器：按当前值重生成为与正式文件 **payload 一字不差**；模拟图 51 个键全覆盖
- 顺带修复生成页样式丢失（上一版替换 CSS 时误删 60 行基础样式，导致版面错乱）

## [未发布] — 2026-11-03（v3.0 第一档：实体槽位表化）

**背景**：推送包里 49 个实体 ID 硬编码在模板各处，换一个用户/换一个实体都要读懂模板。
v3.0 第一档把实体 ID 集中到文件头部的 `SLOT` 槽位表（49 行，带中文注释），
模板只引用 `SLOT.xxx`。

- **payload 与 v2 完全一致**：JSON 键名、顺序、取值逻辑逐键比对无差异；
  MQTT 主题/频率/retain、设备固件全部不动，**无需重编译烧录**
- 换实体 = 只改 SLOT 表右边 → 开发者工具→YAML→自动化 重新加载即生效
- `screen_bright` 保持硬编码（屏幕自身背光，由控制包创建，不开放选择）
- 为第二档（网页版配置生成器）打底：生成器输出 = 填好的 SLOT 表
- **修复（35f0983）**：v3 首版 payload 的字典字面量内部误放 Jinja 注释导致自动化装载失败
  （template value should be a string）；已移出注释并加固——SLOT 兜底 + 59 处引用
  加 `| default('')`，槽位表填错键名时仅该字段显示 `--`，不再拖垮整条推送

## [未发布] — 2026-11-02（v2.1 远程控制通道，基于 v2.0 通知线）

**背景**：亮度 / 亮屏时间 / 两个开关原先只走 ESPHome Native API，要求 HA 能主动连到屏幕。
屏幕带出门（无公网 IP、穿过 NAT）后这条控制线必断；而 MQTT 是设备主动往外连，不受影响。
于是数据一直好、控制全废。本版把控制也搬到 MQTT。

### Added

- **设备端 5 个控制主题**（`mqtt.on_message`，QoS1，全部 retain）：
  `cmd/light`（ON/OFF）、`cmd/bright`（10~100）、`cmd/sleep`（15~900）、
  `cmd/autosleep`（ON/OFF）、`cmd/wake`（ON/OFF）
- **状态回发**：`esphome/ha-monitor-display/state`（retain）一帧 JSON
  `{"light":...,"bright":...,"sleep":...,"autosleep":...,"wake":...}`，
  每次控制量变化 + 开机 20 s 后各发一次，HA 面板实时跟随
- **HA 侧新包** `ha/monitor_display_control.yaml`：5 个 `mqtt` 实体
  （1 灯 + 2 数值 + 2 开关），归到一个「HA Monitor Display 远程控制」设备下

### Changed

- 控制动作全部复用现有实体逻辑（滑块 `set_action` / `switch.turn_on` / 休眠脚本），
  不新增状态变量，本机触摸操作与远程下发走同一条路径

### 注意

- `cmd` 主题 retain → 设备重连/重启会重放 HA 最后一次下发的值，
  即「重启后以 HA 侧为准」（比本机 `restore_value` 更可预期）
- 局域网内原生 API 那 5 个实体与远程这 5 个并存，出门后只剩远程这套可用

---

## [v1.1.1] — 2026-11-01（MQTT 线，当前推荐 / v2.0 前回退基线）

本版只做续航优化，**不动任何界面与数据协议**，可从 v1.1.0 直接 OTA 升级。

### Changed

- **WiFi 省电**：`wifi.power_save_mode: light`（modem-sleep）。数据帧仍为 5 s 一推，实测无感知影响；待机电流明显下降（约省 1/3）
- **默认屏幕亮度 60%**：`ui_saved_brightness` 初值 0.6 成为唯一来源——开机点亮（lvgl `on_boot`）与熄屏恢复同源，不再各写各的；亮度滑块调整后自动回写该全局变量

### Fixed

- 开机满亮闪变：灯实体 `restore_mode` 由 `ALWAYS_ON` 改为 `ALWAYS_OFF`，开机不再自带 100% 点亮，由 `on_boot` 按 `ui_saved_brightness` 点亮

### 实测（真机）

| 状态 | 电流 |
| -- | -- |
| 熄屏待机（60% 亮度 / 5s 推送 / modem-sleep） | **≈ 20 mA** |
| 亮屏 | ≈ 150~180 mA |

续航推算：500 mAh ≈ 21 h，1000 mAh ≈ 42 h，18650 3000 mAh ≈ 一周。

---

## [v1.1.0] — 2026-10-31（MQTT 线）

本月最后一轮大改，观感与功能并重：

- **每页背景色 HA 下拉可调**：`Dashboard / Network / System Bg Color` 三个 select，8 档深色预设（石墨 / 深红 / 深黄 / 墨绿 / 浅蓝 / 深蓝 / 深紫 / 深靛），卡片色随选定色、缝隙取选定色 ×0.5
- **白字规则统一**：静态文字一律纯白，配色改由图标承担（TAB 当前页与区块标题图标统一青 `4FD8FA`）；动态语义色保留（涨跌 / 居家模式 / 车位 / 风扇分档 / SIGQ / 告警 / 低电量数字）
- 车位卡改左右分栏：左列图标 + 车位状态，右栏两行车辆距离（12px）
- 居家模式加音量百分比（随模式色）
- 系统页行 1 加当前时间（SNTP 北京时间，前置黄色时钟图标）
- 今日能耗四行改为 电压 / 水压 / 用气 / 用电；三页 TAB 偏移与行 1 左边界对齐

---

## [v1.0.1] — 2026-10-31（MQTT 线）

1.0 线的稳定定版，全部为观感与数据修正，未新增功能：

- 8 个区块标题加 MDI 图标；页面改名（家居 / 网络运行 / NAS 运行）
- 字库补 19 字；第二轮配色方案落地
- 上证指数涨跌动态着色（涨红跌绿）
- `web_server` 认证改 digest
- NAS 的 CPU / 内存未载入时用基色（不再误报告警色）
- 风扇「开 / ≤50%」状态字改黄

---

## [v1.0] — 2026-10-30（MQTT 线首个定版）

- 三页 UI（家庭 / 网络 / 系统）+ 底部 TAB 触摸导航
- 数据通道：HA 自动化每 5 s `mqtt.publish` 推 50 实体 JSON，屏幕 `on_json_message` 解析进 `hd_*` 全局变量
- 熄屏休眠（可调 15~900 s，触摸即醒）、亮度滑块、断电记忆
- 硬件冻结基线，此后 1.x 线只接受参数微调

---

## [API v0.9.0] — 2026-10-29（API 线，前身版本）

- 数据由 ESPHome 通过 **Native API 从 HA 主动拉取**（`platform: homeassistant` 传感器 / text_sensor / binary_sensor，共 51 处 entity_id），刷新率由各 sensor 的 `update_interval` 决定
- 同时保留 **MQTT/TLS 8883 远程通道**（方案 C 双通道设计）：局域网走 API 低延迟，外网走 MQTT 可远程读取
- 三页 UI 与 MQTT 线同源，但字号体系（12/16/20）与字库（453 字白名单）为早期版本
- 部署时需把主配置里的 entity_id 改成自己 HA 的实际实体
