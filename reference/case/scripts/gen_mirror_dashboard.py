"""生成 HA「屏幕镜像」面板配置 —— 480×320 像素级 1:1 复刻屏幕四页。

设计要点
--------
* 排版取自 ui/page_*.yaml 的实际控件坐标（由 case/scripts/dump_layout.py 导出），
  画布固定 480×320，与屏幕 Lvgl 画布一一对应（1 css px = 1 屏幕 px）。
* 数据全部走 Jinja 从 HA 实体实时取，颜色规则与固件 lambda 一致。
* 图标用 HA 原生 <ha-icon>，不依赖 MDI 字体文件路径。
* 四页 = 面板四视图；屏幕底部 TAB 由 HA 视图标签承担。
* 小屏用 media query 分档缩放（CSS 无法纯声明式等比缩放 480px 画布）。

用法：cd "D:/HA Monitor Display" && python case/scripts/gen_mirror_dashboard.py
输出：../HA Lovelace/lovelace/lovelace_monitor_dashboard.yaml

!!! 已废弃，请勿运行 !!!
本脚本产出的是早期「2 视图（家居/网络）」结构；现行 lovelace_monitor_dashboard.yaml
已改为单视图 panel + 一个 html-template-card 承载 4 页（家居/网络/系统/通知），
由人工维护。直接运行本脚本会覆盖并回退线上成品。
"""
import io
import os

# ---------------------------------------------------------------- 通用
# 屏幕配色（与固件一致）
C_BG = '#0F0F0F'      # 页面底色
C_CARD = '#1E1E1E'    # 区块底色
C_TXT = '#FFFFFF'
C_DIM = '#757575'
C_CYAN = '#4FD8FA'    # 标题图标 / 当前页标识
C_ORANGE = '#FFB74D'
C_PURPLE = '#B39DFF'
C_GREEN = '#59D98B'
C_BLUE = '#5AA9FF'
C_YELLOW = '#FFD54F'
C_RED = '#FF5252'

CSS = """
.hmd{position:relative;width:480px;height:320px;background:%(bg)s;
  font-family:"PingFang SC","Noto Sans SC","Microsoft YaHei",system-ui,sans-serif;
  color:%(txt)s;overflow:hidden;border-radius:8px;transform-origin:top left;
  -webkit-font-smoothing:antialiased;line-height:1}
.hmd *{box-sizing:border-box}
.hmd .c{position:absolute;background:%(card)s;border-radius:10px;
  display:flex;align-items:center;overflow:hidden}
.hmd .r{display:flex;align-items:center;width:100%%;height:100%%;padding-left:6px}
.hmd .col{flex-direction:column;align-items:stretch;padding:0}
.hmd .ln{display:flex;align-items:center;height:22px;padding-left:6px;gap:3px}
.hmd .t16{font-size:16px}
.hmd .t12{font-size:12px}
.hmd .t20{font-size:20px}
.hmd .dim{color:%(dim)s}
.hmd .ttl{font-size:14px;padding-left:6px;height:30px;display:flex;align-items:center;gap:3px}
.hmd .hr{height:1px;background:#FFFFFF;opacity:.85;margin:0 6px 4px 6px}
.hmd .g{display:flex;align-items:center;gap:2px;white-space:nowrap}
.hmd-wrap{display:flex;justify-content:center;padding:2px 0}
@media (max-width:560px){.hmd{transform:scale(.92)}.hmd-wrap{height:296px}}
@media (max-width:520px){.hmd{transform:scale(.84)}.hmd-wrap{height:270px}}
@media (max-width:478px){.hmd{transform:scale(.76)}.hmd-wrap{height:244px}}
@media (max-width:430px){.hmd{transform:scale(.68)}.hmd-wrap{height:218px}}
@media (max-width:386px){.hmd{transform:scale(.60)}.hmd-wrap{height:192px}}
""" % dict(bg=C_BG, card=C_CARD, txt=C_TXT, dim=C_DIM)


def ico(name, size=16, color=C_CYAN):
    """HA 原生图标元素（尺寸走 --mdc-icon-size）。"""
    return (f'<ha-icon icon="mdi:{name}" style="--mdc-icon-size:{size}px;'
            f'color:{color};flex:0 0 auto"></ha-icon>')


def box(x, y, w, h, inner, extra=''):
    return (f'<div class="c" style="left:{x}px;top:{y}px;width:{w}px;'
            f'height:{h}px;{extra}">{inner}</div>')


def row(items, cls='r'):
    return f'<div class="{cls}">' + ''.join(items) + '</div>'


def lab(text, cls='t16', color=None, extra=''):
    st = f'color:{color};' if color else ''
    return f'<span class="{cls}" style="{st}{extra}">{text}</span>'


def page(inner):
    return f'<div class="hmd-wrap"><div class="hmd">{inner}</div></div>'


# ---------------------------------------------------------------- 通用 Jinja 片段
J_VAL = "{{ states('%s') }}"


def num(eid, nd=0, unit=''):
    """数值显示；无数据时灰 --。"""
    return ("{% set v = states('%s') %s %s {{ '--' if v in ['unknown','unavailable','none'] "
            "else v | float(0) | round(%d) }}{%s}" % (eid, '%}', '', nd, unit))


# ---------------------------------------------------------------- 页 1 家居
def pg_home():
    # 行 1：时间 | 天气 | 上证
    h1 = row([
        lab("{{ states('sensor.zhong_wen_shi_jian') }}", 't16'),
        f'<span style="flex:0 0 128px"></span>',
        ico('weather-partly-cloudy', 18, C_CYAN),
        lab("{{ state_attr('weather.tian_qi','temperature') | round(0) | int }}°", 't16'),
        f'<span style="flex:0 0 40px"></span>',
        ico('chart-line', 18, C_CYAN),
        lab('上证:', 't16'),
        lab("""{% set s = state_attr('sensor.mei_ri_gu_zhi','sh000001') %}
{% if s is mapping and s.price is defined %}{{ '%.2f' | format(s.price | float(0)) }}{% else %}--{% endif %}""",
            't16', extra="{% set s = state_attr('sensor.mei_ri_gu_zhi','sh000001') %}"
                         "{% set cr = (s.changeRatio | float(0)) if (s is mapping and s.changeRatio is defined) else 0 %}"
                         "color:{{ '#FF5252' if cr > 0 else ('#59D98B' if cr < 0 else '#FFFFFF') }}"),
    ])

    # 行 2：在家 / 客人 / 手机 / 语音（四格，整格动态色）
    def quad(eid, icon, name, color, unit_color=None):
        # 值 >0 → 该格图标与名称着色；=0 → 灰
        return box(0, 0, 0, 0, '')  # 占位，下面重写

    quads = []
    specs = [
        ('sensor.family_home_count', 'home-account', '在家', C_ORANGE),
        ('sensor.guest_visit_count', 'account-multiple', '客人', C_PURPLE),
        ('sensor.phone_online_count', 'cellphone', '手机', C_GREEN),
        ('sensor.voice_broadcast', 'microphone', '语音', C_BLUE),
    ]
    xs = [5, 126, 249, 370]
    for i, (eid, icon, name, col) in enumerate(specs):
        if eid == 'sensor.voice_broadcast':
            body = ('{% set on = is_state(\'switch.voice_broadcast\',\'on\') %}'
                    f'{ico(icon, 16, "{{ \'#5AA9FF\' if on else \'#757575\' }}")}'
                    f'<span class="t12" style="color:{{{{ \'#FFFFFF\' }}}}">{name}: '
                    '{{ \'开\' if on else \'关\' }}</span>')
        else:
            body = (f"{{% set n = states('{eid}') | int(0) %}}"
                    f'{ico(icon, 16, "{{ \'" + col + "\' if n > 0 else \'#757575\' }}")}'
                    f'<span class="t12" style="color:{{% raw %}}{{% endraw %}}">{name}: '
                    f'{{{{ n if n > 0 else \'--\' }}}}</span>')
        quads.append(box(xs[i], 61, 105, 41, row([body])))

    # 行 3：居家模式 | 车位
    mode = (
        f"{{% set p = state_attr('sensor.ju_jia_mo_shi','volume_percent') %}}"
        + ico('home-heart', 18, "{{ '#59D98B' if '在家' in states('sensor.ju_jia_mo_shi') else ('#FF5252' if '离家' in states('sensor.ju_jia_mo_shi') else '#FFFFFF') }}")
        + '<span class="t20">{{ states(\'sensor.ju_jia_mo_shi\') }}'
          '{% if p %}<span class="t12" style="color:#B0B0B0"> {{ p }}</span>{% endif %}</span>'
    )
    parking = (
        ico('car', 18, C_YELLOW)
        + '<span class="t16">{{ states(\'sensor.parking_status\') }}</span>'
        + '<span style="flex:1"></span>'
        + '<div style="display:flex;flex-direction:column;gap:2px;padding-right:6px">'
        + '<span class="t12" style="color:#FFD54F">轩逸 {{ state_attr(\'sensor.parking_status\',\'xuanyi\').location if state_attr(\'sensor.parking_status\',\'xuanyi\') else \'--\' }}</span>'
        + '<span class="t12" style="color:#F48FB1">比亚迪 {{ state_attr(\'sensor.parking_status\',\'beyond\').location if state_attr(\'sensor.parking_status\',\'beyond\') else \'--\' }}</span>'
        + '</div>'
    )

    # 列 1：电器动态（4 行）
    col1_items = [
        ('sensor.light_on_count', 'lightbulb-group', '电灯', C_ORANGE),
        ('sensor.curtain_closed_count', 'curtains', '窗帘', C_PURPLE),
        ('sensor.climate_on_count', 'air-conditioner', '空调', C_BLUE),
        ('sensor.equipment_on_count', 'power-plug', '电器', C_GREEN),
    ]
    col2_items = [
        ('sensor.tasmota_energy_voltage', 'flash', '电压', C_YELLOW, 'V'),
        ('sensor.maze_wateronev3_tp_f8e644', 'water', '水压', C_BLUE, ''),
        ('sensor.ri_yong_qi_liang', 'fire', '用气', C_YELLOW, ''),
        ('sensor.tasmota_energy_today', 'chart-bar', '用电', C_GREEN, 'kWh'),
    ]

    def col(title, icon, items, total):
        lines = []
        for it in items:
            eid, ic, nm, cl = it[0], it[1], it[2], it[3]
            unit = it[4] if len(it) > 4 else ''
            s = states_fmt(eid, unit)
            lines.append(f'<div class="ln"><div class="g">{ico(ic, 14, cl)}'
                         f'<span class="t12">{nm}: {s}</span></div></div>')
        return ('<div class="c col" style="left:%dpx;top:162px;width:%dpx;height:101px">'
                '<div class="ttl">{{% set t = 0 %}}%s<span class="t12">%s</span></div>'
                '<div class="hr" style="width:100px;margin-left:10px"></div>%s</div>'
                % (0, 0, ico(icon, 14, C_CYAN), title, ''.join(lines)))

    c1 = col('电器动态', 'lightbulb-group', col1_items, 0).replace('left:0px;top:162px;width:0px', 'left:5px;top:162px;width:154px')
    c2 = col('今日能耗', 'lightning-bolt', col2_items, 0).replace('left:0px;top:162px;width:0px', 'left:162px;top:162px;width:154px')

    # 右列两格：Nova13 / Nova12
    def dev(y, eid, name):
        return box(319, y, 156, 49, row([
            ico('cellphone-screenshot' if 'nova13' in eid else 'cellphone', 16, C_BLUE),
            lab(name, 't12'),
            '<span style="flex:1"></span>',
            lab("{{ '在线' if is_state('%s','on') else '离线' }}" % eid, 't12'),
        ]), 'padding-right:8px')

    inner = (
        box(5, 5, 470, 50, h1)
        + ''.join(quads)
        + box(5, 110, 233, 49, row([mode]), 'padding-left:4px')
        + box(241, 110, 234, 49, row([parking]))
        + c1 + c2
        + dev(162, 'binary_sensor.lam_nova13', 'Nova13')
        + dev(214, 'binary_sensor.su_nova12', 'Nova12')
    )
    return page(inner)


def states_fmt(eid, unit=''):
    """值 + 单位；无数据显示灰 --。"""
    u = f' {unit}' if unit else ''
    return ("{% set v = states('%s') %%}{{ '--' if v in ['unknown','unavailable','none',''] "
            "else v | float(0) | round(1 if (v | float(0)) % 1 else 0) }}%s" % (eid, u))


# ---------------------------------------------------------------- 页 2 网络
def pg_net():
    def pct(v):
        return v

    h1 = row([
        ico('earth', 16, C_CYAN),
        lab('外网IP:', 't16'),
        lab("{{ states('sensor.tp_link_smb_tl_r498gpm_ac_external_ip') }}", 't16'),
        '<span style="flex:1"></span>',
        ico('clock-outline', 16, C_CYAN),
        lab('已连接:', 't16'),
        lab("""{% set u = states('sensor.tp_link_smb_tl_r498gpm_ac_uptime') | int(0) %}
{{ '%d天%d小时' | format(u // 86400, (u % 86400) // 3600) }}""", 't16'),
        '<span style="flex:0 0 8px"></span>',
    ])

    quads = []
    specs = [
        ('sensor.server_online_count', 'server', '主机', C_ORANGE),
        ('sensor.gateway_online_count', 'router-network', '网关', C_PURPLE),
        ('sensor.ap_online_count', 'wifi', '无线', C_GREEN),
        ('sensor.device_monitor_count', 'devices', '设备', C_BLUE),
        ('sensor.asr_online_count', 'microphone-message', '语音', C_YELLOW),
    ]
    xs = [5, 102, 199, 296, 392]
    ws = [84, 84, 84, 83, 83]
    for i, (eid, icon, name, col) in enumerate(specs):
        body = (ico(icon, 14, col)
                + f'<span class="t12">{name}: {states_fmt(eid)}</span>')
        quads.append(box(xs[i], 61, ws[i], 41, row([body])))

    def col3(x, w, title, icon, items):
        lines = []
        for it in items:
            eid, ic, nm, cl = it[0], it[1], it[2], it[3]
            lines.append(f'<div class="ln"><div class="g">{ico(ic, 14, cl)}'
                         f'<span class="t12">{nm}: {it[4]}</span></div></div>')
        return (f'<div class="c col" style="left:{x}px;top:110px;width:{w}px;height:153px">'
                f'<div class="ttl">{ico(icon, 14, C_CYAN)}<span class="t12">{title}</span></div>'
                f'<div class="hr" style="width:100px;margin-left:10px"></div>{lines and "".join(lines)}</div>')

    c1 = col3(5, 155, '网络运行', 'lan-connect', [
        ('sensor.router_online_count', 'router', '路由在线', C_ORANGE, states_fmt('sensor.router_online_count')),
        ('sensor.device_control_count', 'remote', '控制设备', C_PURPLE, states_fmt('sensor.device_control_count')),
        ('sensor.terminal_online_count', 'laptop', '终端在线', C_GREEN, states_fmt('sensor.terminal_online_count')),
        ('sensor.low_battery_count', 'battery-alert', '低电量数', C_YELLOW, states_fmt('sensor.low_battery_count')),
    ])
    c2 = col3(163, 155, 'NAS运行', 'nas', [
        ('sensor.lamnas_ws_cpu_utilization_total', 'cpu-64-bit', 'CPU利用', C_ORANGE,
         states_fmt('sensor.lamnas_ws_cpu_utilization_total', '%')),
        ('sensor.lamnas_ws_memory_usage_real', 'memory', '内存可用', C_PURPLE,
         states_fmt('sensor.lamnas_ws_memory_usage_real', '%')),
        ('sensor.lamnas_ws_upload_throughput', 'upload', '上传', C_GREEN,
         "{{ (states('sensor.lamnas_ws_upload_throughput') | int(0) / 1024) | round(0) | int }}KB/s"),
        ('sensor.lamnas_ws_download_throughput', 'download', '下载', C_BLUE,
         "{{ (states('sensor.lamnas_ws_download_throughput') | int(0) / 1024) | round(0) | int }}KB/s"),
    ])
    c3 = col3(321, 154, '风扇运行', 'fan', [
        ('fan.fan_pwm_controller_fan_1', 'fan', '前扇', C_BLUE, fan_txt('fan.fan_pwm_controller_fan_1')),
        ('fan.fan_pwm_controller_fan_2', 'fan', '后扇', C_PURPLE, fan_txt('fan.fan_pwm_controller_fan_2')),
        ('switch.ruo_dian_xiang_feng_shan_sonoff_1002b4248d_1', 'fan-chevron-down', '进扇', C_GREEN,
         "{{ '开' if is_state('switch.ruo_dian_xiang_feng_shan_sonoff_1002b4248d_1','on') else '关' }}"),
        ('switch.ruo_dian_xiang_feng_shan_sonoff_1002b4248d_2', 'fan-chevron-up', '出扇', C_ORANGE,
         "{{ '开' if is_state('switch.ruo_dian_xiang_feng_shan_sonoff_1002b4248d_2','on') else '关' }}"),
    ])
    return page(box(5, 5, 470, 50, h1) + ''.join(quads) + c1 + c2 + c3)


def fan_txt(eid):
    return ("{% set p = state_attr('%s','percentage') | int(0) %}"
            "{%% if is_state('%s','off') %%}<span style=\"color:#757575\">停</span>"
            "{%% else %%}<span style=\"color:{%% if p > 80 %%}#FF5252{%% elif p > 50 %%}#FFB74D{%% else %%}#59D98B{%% endif %%}\">{p}%%</span>{%% endif %%}"
            % (eid, eid))


# ---------------------------------------------------------------- 页 3 系统
def pg_sys():
    h1 = row([
        ico('monitor-dashboard', 16, C_CYAN),
        lab("{{ states('sensor.hmd_device_name') if states('sensor.hmd_device_name') not in ['unknown','unavailable'] else 'HA Monitor Display' }}", 't16'),
        '<span style="flex:1"></span>',
        ico('timer-outline', 16, C_CYAN),
        lab("{{ as_timestamp(now()) | int - (states('sensor.ha_uptime_seconds') | int(0)) | int if false else '' }}", 't16'),
        '<span style="flex:0 0 8px"></span>',
    ])
    return page(box(5, 5, 470, 50, h1))


# ---------------------------------------------------------------- 组装 YAML
def yaml_card(html, title=''):
    out = ['      - type: custom:html-template-card']
    if title:
        out.append(f'        title: {title}')
    out.append('        ignore_line_breaks: true')
    out.append('        content: |')
    for ln in html.split('\n'):
        out.append('          ' + ln)
    return '\n'.join(out)


def build():
    pages = [
        ('家居', 'hmd-home', 'mdi:home', pg_home()),
        ('网络', 'hmd-net', 'mdi:lan', pg_net()),
    ]
    head = """# ==========================================================
# HA Monitor Display —— 屏幕镜像（480×320 像素级 1:1 复刻）
# 本文件由 case/scripts/gen_mirror_dashboard.py 生成，请勿手改
# ==========================================================
title: 屏幕镜像

views:
"""
    body = []
    for title, path, icon, html in pages:
        body.append(f'  - title: {title}\n    path: {path}\n    icon: {icon}\n    cards:\n')
        body.append(yaml_card(CSS + html) + '\n')
    io.open(os.path.join('..', 'HA Lovelace', 'lovelace', 'lovelace_monitor_dashboard.yaml'), 'w', encoding='utf-8').write(head + ''.join(body))
    print('written ../HA Lovelace/lovelace/lovelace_monitor_dashboard.yaml')


if __name__ == '__main__':
    build()
