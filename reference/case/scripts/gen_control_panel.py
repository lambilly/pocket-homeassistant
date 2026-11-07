# -*- coding: utf-8 -*-
"""生成「掌控」Lovelace 面板。

设计目标：手机优先的全屋操作台，与「概览」（桌面四栏全景）、「屏幕镜像」（墙屏复刻）分工互补。
视图顺序：此刻 / 能源 / 房间 / 安防（页长以能源页为基准，长出来的整合）。
产物：D:/HA Lovelace/lovelace/lovelace_phone_dashboard.yaml（不推送 HA，等用户确认）

用法：python case/scripts/gen_control_panel.py
"""
import io
import json
import os
import yaml

# ---------------------------------------------------------------- 数据

W_MAP = {
    'clear-night': '晴夜', 'cloudy': '多云', 'exceptional': '极端', 'fog': '雾',
    'hail': '冰雹', 'lightning': '雷雨', 'lightning-rainy': '雷阵雨',
    'partlycloudy': '多云', 'pouring': '暴雨', 'rainy': '雨', 'snowy': '雪',
    'snowy-rainy': '雨夹雪', 'sunny': '晴', 'windy': '大风', 'windy-variant': '大风',
}

CLIMATE_MAP = {'off': '关闭', 'on': '开启', 'cool': '冷', 'heat': '热', 'dry': '除湿',
               'fan_only': '送风', 'auto': '自动', 'unavailable': '离线'}

DOORS = [
    ('大门', 'binary_sensor.e4aaec82f917_contact'),
    ('后门', 'binary_sensor.e4aaec830af5_contact'),
    ('主卧门', 'binary_sensor.e4aaecaacf62_contact'),
    ('次卧门', 'binary_sensor.e4aaecab36c0_contact'),
    ('书房门', 'binary_sensor.e4aaec8a8821_contact'),
    ('主卫门', 'binary_sensor.e4aaec8d0598_contact'),
    ('公卫门', 'binary_sensor.e4aaec8a3d86_contact'),
    ('酒柜门', 'binary_sensor.e4aaec8d1bf9_contact'),
    ('工具柜门', 'binary_sensor.e4aaec8a568f_contact'),
    ('储物间门', 'binary_sensor.chu_wu_jian_men_chuan_gan_qi_opening'),
]
WINDOWS = [
    ('阳台窗', 'binary_sensor.e4aaecd80bcc_contact', 'mdi:window-open-variant'),
    ('水房窗', 'binary_sensor.e4aaec8a2f3e_contact', 'mdi:window-open-variant'),
    # 帘用上下卷帘图标（用户 11-05 指定）
    ('书房帘', 'binary_sensor.e4aaec92af35_contact', 'mdi:roller-shade'),
    ('次卧帘', 'binary_sensor.e4aaec92af38_contact', 'mdi:roller-shade'),
]
ALARMS = [
    ('烟感', 'binary_sensor.18c23c2c8f38_smoke', 'mdi:smoke-detector-variant', '厨房'),
    ('燃气', 'binary_sensor.gas_alarm_sensor_gas_alarm', 'mdi:fire-alert', '水房'),
    ('水浸', 'binary_sensor.18c23c2f9184_water_leak', 'mdi:water-alert', '水房'),
    ('漏水', 'binary_sensor.maze_wateronev3_tp_f8e644_water', 'mdi:pipe-leak', '阳台'),
]

ROOMS = [
    dict(name='客厅', icon='mdi:sofa', temp='sensor.a4c13825caa2_temperature',
         hum='sensor.a4c13825caa2_humidity', light='light.ke_ting_deng_guang',
         cover=None, climate='climate.208907215082288_climate',
         doors=['binary_sensor.e4aaec82f917_contact'], motion='binary_sensor.motion_sensor_910e_motion'),
    # 餐厅无独立温湿度计，借用客厅温湿度计（用户确认，2026-11-05）
    dict(name='餐厅', icon='mdi:silverware-fork-knife', temp='sensor.a4c13825caa2_temperature',
         hum='sensor.a4c13825caa2_humidity',
         light='light.can_ting_deng_guang', cover='cover.sonoff_100237ed13', climate=None,
         doors=['binary_sensor.e4aaec8d1bf9_contact'],
         motion='binary_sensor.linp_cn_1110644278_hb01_occupancy_status_p_2_1'),
    dict(name='厨房', icon='mdi:stove', temp='sensor.a4c1386a89bf_temperature',
         hum='sensor.a4c1386a89bf_humidity', light='light.chu_fang_deng_guang',
         cover=None, climate=None, doors=[],
         motion='binary_sensor.linp_cn_1084416875_hb01_occupancy_status_p_2_1'),
    dict(name='主卧', icon='mdi:bed-king', temp='sensor.a4c1380d8e91_temperature',
         hum='sensor.a4c1380d8e91_humidity', light='light.zhu_wo_deng_guang',
         cover='cover.lumi_hmcn02_ecb8_curtain', climate='climate.208907213270301_climate',
         doors=['binary_sensor.e4aaecaacf62_contact'], motion='binary_sensor.dc8e952a3a60_motion'),
    dict(name='次卧', icon='mdi:bed-single', temp='sensor.a4c138ecda90_temperature',
         hum='sensor.a4c138ecda90_humidity', light='light.ci_wo_deng_guang',
         cover='cover.ciwo_curtain', climate='climate.210006724901473_climate',
         doors=['binary_sensor.e4aaecab36c0_contact'], motion='binary_sensor.e0798db0bf78_motion'),
    dict(name='书房', icon='mdi:desk',
         temp='sensor.miaomiaoc_cn_blt_3_1fmkveql04o00_t1_temperature_p_2_1',
         hum='sensor.miaomiaoc_cn_blt_3_1fmkveql04o00_t1_relative_humidity_p_2_2',
         light='light.shu_fang_deng_guang',
         cover='cover.shufang_curtain', climate='climate.210006724901502_climate',
         doors=['binary_sensor.e4aaec8a8821_contact'], motion='binary_sensor.e406bf9f540f_motion'),
    dict(name='阳台', icon='mdi:balcony',
         temp='sensor.linp_cn_blt_3_1gqpeobb84s01_ks1bp_temperature_p_2_1001',
         hum='sensor.linp_cn_blt_3_1gqpeobb84s01_ks1bp_relative_humidity_p_2_1008',
         light='light.yang_tai_deng_guang',
         cover='cover.yang_tai_chuang_lian', climate=None,
         doors=['binary_sensor.e4aaecd80bcc_contact'], motion='binary_sensor.e406bf9f4511_motion'),
    dict(name='水房', icon='mdi:water-boiler', temp='sensor.a4c138ca51ee_temperature',
         hum='sensor.a4c138ca51ee_humidity', light='light.shui_fang_deng_switch',
         cover=None, climate=None,
         doors=['binary_sensor.e4aaec830af5_contact'], motion='binary_sensor.187a3ebfc161_motion'),
    dict(name='公卫', icon='mdi:toilet', temp='sensor.a4c138b657de_temperature',
         hum='sensor.a4c138b657de_humidity', light='light.gong_wei_deng_guang',
         cover=None, climate=None,
         doors=['binary_sensor.e4aaec8a3d86_contact'], motion='binary_sensor.187a3ec94481_motion',
         accent='#5AA9FF'),  # 公卫固定蓝色兜底（用户 11-05）
    dict(name='主卫', icon='mdi:shower', temp='sensor.a4c1385bff0e_temperature',
         hum='sensor.a4c1385bff0e_humidity', light='light.zhu_wei_deng_guang',
         cover=None, climate=None,
         doors=['binary_sensor.e4aaec8d0598_contact'], motion='binary_sensor.e0798dba5b63_motion'),
]

CLIMATES = ['climate.208907215082288_climate', 'climate.208907213270301_climate',
            'climate.210006724901473_climate', 'climate.210006724901502_climate']

# 每个房间一个色条（顺次取色，相同房间每次生成结果稳定）
ACCENTS = ['#5AA9FF', '#59D98B', '#FFB74D', '#B39DFF', '#4FD8FA', '#FFD54F',
           '#FF8A65', '#80CBC4', '#9FA8DA', '#F48BF1', '#AED581', '#E57373']

# ---------------------------------------------------------------- 组件


def hexa(c, a):
    c = c.lstrip('#')
    return f'rgba({int(c[0:2], 16)},{int(c[2:4], 16)},{int(c[4:6], 16)},{a})'


def tmpl_card(primary, secondary=None, icon=None, color=None, entity=None,
              tap='more-info', vertical=False, multiline=True, dense=False,
              pad=None, isize=None, lh=None, fs=None, pcol=None, pw=None):
    """mushroom-template-card —— 一律左右结构：左图标、右两行文字（主行 + 次行）。

    行距用 mushroom 暴露的 --mush-card-*-line-height 收紧，避免两行之间拉得很开。
    dense=True 用于三列小格（房间页的灯/窗帘/空调），图标与字号再降一档。
    """
    c = {'type': 'custom:mushroom-template-card'}
    if entity:
        c['entity'] = entity
    if icon:
        c['icon'] = icon
    c['primary'] = primary
    if secondary is not None:
        c['secondary'] = secondary
        if multiline:
            c['multiline_secondary'] = True
    if color:
        c['color'] = color
    if vertical:
        c['vertical'] = True
    c['icon_tap_action'] = {'action': tap}
    pf, pl, sf, sl, ico, padpx = (('12.5px', '15px', '11px', '12px', '24px', '5px 8px')
                                if dense else
                                ('13.5px', '16px', '11.5px', '13px', '30px', '6px 10px'))
    pl, sl = lh or (pl, sl)
    pf, sf = fs or (pf, sf)
    ico = isize or ico
    pad = pad or padpx
    c['card_mod'] = {'style': (
        'ha-card {\n'
        f'  --mush-card-primary-font-size: {pf};\n'
        f'  --mush-card-primary-line-height: {pl};\n'
        f'  --mush-card-secondary-font-size: {sf};\n'
        f'  --mush-card-secondary-line-height: {sl};\n'
        f'  --mush-icon-size: {ico};\n'
        + (f'  --mush-card-primary-color: {pcol};\n' if pcol else '')
        + (f'  --mush-card-primary-font-weight: {pw};\n' if pw else '')
        + f'  padding: {pad} !important;\n'
        '}')}
    return c


def room_block(head, btns, accent='#5AA9FF', cols=None):
    """一块容器：左侧色条 + 标题行（同色渐变底 + 同色分隔线）+ 芯片卡片。
    块内每张卡都是独立「芯片」（深底 + 细边框 + 圆角），层次与监控块一致；
    芯片之间靠 grid gap 分隔，不再加行线。"""
    def flatten(c):
        cm = c.setdefault('card_mod', {})
        st = cm.get('style') or 'ha-card {\n}'
        body, tail = st.rsplit('}', 1)
        cm['style'] = (body + '  background: transparent !important;\n'
                       '  border: none !important;\n'
                       '  border-radius: 0 !important;\n'
                       '  box-shadow: none !important;\n' + tail)

    def chip(c):
        cm = c.setdefault('card_mod', {})
        st = cm.get('style') or 'ha-card {\n}'
        body, tail = st.rsplit('}', 1)
        cm['style'] = (body +
                       '  background: var(--ha-card-background, #1c1c1e) !important;\n'
                       '  border: 1px solid var(--divider-color, #2a2a2a) !important;\n'
                       '  border-radius: 12px !important;\n'
                       '  box-shadow: none !important;\n' + tail)

    flatten(head)
    head['card_mod']['style'] = head['card_mod']['style'].replace(
        '}', '  background: linear-gradient(90deg, ' + hexa(accent, .26) +
        ' 0%, ' + hexa(accent, .06) + ' 70%, transparent 100%) !important;\n'
        '  box-shadow: inset 0 -1px 0 ' + hexa(accent, .55) + ' !important;\n}', 1)
    for c in btns:
        chip(c)

    n = cols or len(btns) or 1
    blk = stack([head, grid(btns, n)])
    blk['card_mod'] = {'style': (
        'ha-card {\n'
        '  background: var(--ha-card-background, var(--card-background-color)) !important;\n'
        '  border: 1px solid ' + hexa(accent, .42) + ' !important;\n'
        '  border-left: 5px solid ' + accent + ' !important;\n'
        '  border-radius: 14px !important;\n'
        '  overflow: hidden;\n'
        '  box-shadow: 0 2px 10px rgba(0,0,0,.28) !important;\n'
        '}')}
    return blk


def sec_head(title, accent, note=None, icon=None):
    ico = ('<ha-icon icon="' + icon + '" style="color:' + accent +
           ';--mdc-icon-size:17px;flex:none"></ha-icon>' if icon else '')
    return html(
        '<div style="display:flex;align-items:center;gap:6px">'
        + ico
        + '<span style="font-size:14.5px;font-weight:700;line-height:17px;color:' + accent + '">'
        + title + '</span>'
        + ('<span style="font-size:11.5px;opacity:.5;line-height:17px">' + note + '</span>'
           if note else '')
        + '</div>', pad='13px 9px 8px')


def section(title, accent, cards, cols=None, note=None, icon=None):
    """区块 = 彩色标题行（带图标）+ 卡片，外观与房间块完全一致。
    页面级垂直罗列（max_columns:1），块内卡片保持原并排布局（用户 11-05 澄清）。"""
    return room_block(sec_head(title, accent, note, icon), cards, accent, cols)


def grid(cards, columns=2):
    return {'type': 'grid', 'columns': columns, 'square': False, 'cards': cards}


def stack(cards):
    return {'type': 'custom:stack-in-card', 'mode': 'vertical', 'cards': cards}


def html(content, pad='2px 4px'):
    # html-template-card 的 setConfig 会写行内 padding:16px，必须用 !important 压掉，
    # 间距全部由 content 里的 div 自己控制（否则真机上标题/分隔线四周会多一圈 16px）。
    return {'type': 'custom:html-template-card',
            'content': f'<div style="padding:{pad}">{content}</div>',
            'card_mod': {'style': 'ha-card {\n  padding: 0 !important;\n}'}}


ON_OFF = "{{ '开启' if is_state('%s','on') else '关闭' }}"

# ---------------------------------------------------------------- 语义色（全站唯一口径）
# 有色 = 该设备此刻「在做点什么」，灰色 = 关闭 / 未激活 / 无数据；红色只给需要留意的事。
C_ON = '#FFB74D'     # 开启/活动：灯开、窗帘开、有人活动
C_OK = '#59D98B'     # 正常/在线：设备在线、安防无异常、门关（在安防详情卡里）
C_RUN = '#5AA9FF'    # 运行/制冷：空调开、语音播报开、功率
C_LINK = '#4FD8FA'   # 通讯/连接：手机在线、监控在线、屏幕在线
C_CURT = '#B39DFF'    # 窗帘（类别色，与中控一致）
C_VOICE = '#59D98B'   # 语音播报（类别色，绿色）
C_NUM = '#B39DFF'    # 计量/计数：本月累计、车辆距离
C_MONEY = '#FFD54F'  # 费用/能耗：电费、用电、水气
C_BAD = '#FF5252'    # 异常/告警：门开、窗开、传感器触发、设备离线
C_OFF = '#757575'    # 关闭/未激活/无数据（整卡灰）

# 视图可见性：掌控 4 个视图仅对「林宗华」账号显示（用户 11-05 在 HA UI 里设定）。
# 生成器必须保留这段，否则重跑会把可见性限制冲掉。删掉/清空 = 所有人可见。
VIEW_VISIBLE = [{'user': '0044ffb90aab45e799df1532f6586d71'}]   # 林宗华
AMBER_GREY = "{{ '" + C_ON + "' if is_state('%s','on') else '" + C_OFF + "' }}"


def cg(expr, color=C_ON, off=C_OFF):
    """状态色：expr 为真 → color，否则灰（整卡灰）。"""
    return "{{ '" + color + "' if (" + expr + ") else '" + off + "' }}"

VACUUM_MAP = "{'error':'异常','docked':'已回充','cleaning':'清扫中','returning':'返航中','idle':'待机','paused':'暂停','unavailable':'离线'}"
DIR_MAP = "{'arrived':'已到达','stationary':'静止','towards':'正在接近','away_from':'正在远离'}"


# ---------------------------------------------------------------- 视图 1 此刻

def view_now():
    # 问候行：不用 user.name —— html-template-card 在部分前端版本取不到 user 上下文，
    # 模板抛 UndefinedError 会让整张卡渲染空白（用户真机复现），名字直接写死，属性全部兜底
    greet = ("{% set g = state_attr('sensor.zhong_wen_shi_jian','greet') or {} %}"
             "主人，{{ g.helloWord or '你好' }}")
    wm = json.dumps(W_MAP, ensure_ascii=False).replace('"', "'")
    head = html(
        '<div style="font-size:19px;font-weight:600;line-height:1.3">' + greet + '</div>'
        '<div style="font-size:12.5px;opacity:.62;margin-top:3px">'
        "{% set s = state_attr('sensor.zhong_wen_shi_jian','solar') or {} %}"
        "{% set l = state_attr('sensor.zhong_wen_shi_jian','lunar') or {} %}"
        "{% set wm = " + wm + " %}"
        "{{ s.date_cn }} {{ s.week_cn }} · {{ l.date }} · "
        "{{ wm.get(states('weather.tian_qi'), states('weather.tian_qi')) }} "
        "{{ state_attr('weather.tian_qi','temperature') | round(0) | int }}°C</div>",
        pad='8px 15px 2px')

    home = [
        tmpl_card('{{ states("sensor.family_home_count") }} 人在家',
                  # 0 人在家时次行也不能空（用户 11-05：与其他三卡保持两行）
                  "{% set fc = state_attr('sensor.family_home_count','family_count') or {} %}"
                  "{{ fc.family_home_list or ('最近 ' ~ (fc.family_recently_list or '--')) }}",
                  'mdi:account-group',
                  cg("states('sensor.family_home_count')|int(0) > 0"),
                  'sensor.family_home_count'),
        tmpl_card('{{ states("sensor.ju_jia_mo_shi") }}',
                  "音量 {{ state_attr('sensor.ju_jia_mo_shi','volume_percent') }}",
                  'mdi:home-heart',
                  # 模式色（用户 11-05）：离家红 / 休息紫 / 影音黄 / 在家橙 / 其他灰，与中控一致
                  ("{{ '#FF5252' if is_state('sensor.ju_jia_mo_shi','离家模式') else "
                   "'#B39DFF' if is_state('sensor.ju_jia_mo_shi','休息模式') else "
                   "'#FFD54F' if is_state('sensor.ju_jia_mo_shi','影音模式') else "
                   "'#FFA726' if is_state('sensor.ju_jia_mo_shi','在家模式') else '#757575' }}"),
                  'sensor.ju_jia_mo_shi'),
        tmpl_card('Nova13',
                  "{{ '在线' if is_state('binary_sensor.lam_nova13','on') else '离线' }}",
                  'mdi:cellphone', '#5AA9FF',  # Nova13·蓝（设备身份色，用户 11-05）
                  'binary_sensor.lam_nova13', tap='more-info'),
        tmpl_card('Nova12',
                  "{{ '在线' if is_state('binary_sensor.su_nova12','on') else '离线' }}",
                  'mdi:cellphone', '#B39DFF',  # Nova12·紫（设备身份色，用户 11-05）
                  'binary_sensor.su_nova12', tap='more-info'),
    ]

    quick = [
        tmpl_card('全屋灯光',
                  "{{ state_attr('sensor.light_on_count','light_on_count') | default(states('sensor.light_on_count')) }}"
                  " / {{ state_attr('sensor.light_on_count','light_all_count') }} 盏",
                  'mdi:lightbulb-group', C_ON,  # 0 开也保留灯橙（用户 11-05）
                  'light.quan_wu_deng_guang', tap='toggle'),
        tmpl_card('全屋窗帘',
                  "{{ state_attr('sensor.curtain_closed_count','curtain_open_count') }} 开 · "
                  "{{ state_attr('sensor.curtain_closed_count','curtain_closed_count') }} 关",
                  'mdi:curtains', C_CURT,  # 0 开也保留帘紫（用户 11-05）
                  'cover.quan_wu_chuang_lian', tap='toggle'),
        tmpl_card('全屋空调',
                  "{{ states('sensor.climate_on_count') }} / "
                  "{{ state_attr('sensor.climate_on_count','climate_all_count') }} 运行",
                  'mdi:snowflake-off',
                  C_RUN,  # 0 开也保持空调蓝（用户 11-05）
                  None, tap='call-service'),
        tmpl_card('全屋语音', ON_OFF % 'switch.voice_broadcast',
                  'mdi:bullhorn', cg("is_state('switch.voice_broadcast','on')", C_VOICE),
                  'switch.voice_broadcast', tap='toggle'),
    ]
    # 全屋空调需要 target 列表
    quick[2]['icon_tap_action'] = {
        'action': 'call-service', 'service': 'climate.turn_off',
        'target': {'entity_id': CLIMATES}}

    doors_expr = ", ".join(f"'{e}'" for _, e in DOORS)
    alarm_expr = ", ".join(f"'{e}'" for _, e, _, _ in ALARMS)
    sec = ("{% set d = expand(" + doors_expr + ") %}"
           "{% set a = expand(" + alarm_expr + ") %}"
           "{{ d | selectattr('state','eq','on') | list | count }} 处门未关 · "
           "{% set ab = a | selectattr('state','eq','on') | list %}"
           "{{ '告警 ' ~ (ab | count) ~ ' 项' if ab | count else '无告警' }}")
    col = ("{% set d = expand(" + doors_expr + ") %}"
           "{% set a = expand(" + alarm_expr + ") %}"
           "{{ '" + C_BAD + "' if (d | selectattr('state','eq','on') | list | count) + "
           "(a | selectattr('state','eq','on') | list | count) > 0 else '" + C_OK + "' }}")
    security = tmpl_card('安防', sec, 'mdi:shield-home-outline', col, None,
                         tap='navigate', vertical=False)
    security['icon_tap_action'] = {'action': 'navigate', 'navigation_path': '/phone-dashboard/security'}
    security['tap_action'] = {'action': 'navigate', 'navigation_path': '/phone-dashboard/security'}

    # 今日四项压成两卡（页长向能源页看齐）：一卡两个数值
    today = [
        tmpl_card("电费 ¥{{ states('sensor.jin_ri_dian_fei') }}",
                  "用电 {{ states('sensor.tasmota_energy_today') | round(2) }} 度",
                  'mdi:currency-cny', C_MONEY, 'sensor.jin_ri_dian_fei'),
        tmpl_card("用水 {{ states('sensor.maze_wateronev3_tp_f8e644_daily_water_usage') | round(1) }} L",
                  "用气 {{ states('sensor.ri_yong_qi_liang') }} m³",
                  'mdi:water', C_LINK, 'sensor.maze_wateronev3_tp_f8e644_daily_water_usage'),
    ]

    # 车（原独立「车」TAB 已并入此处）：轩逸 / 比亚迪 各一行，电动车 + 停车并排一行
    cars_a = [
        tmpl_card("轩逸 · {{ states('sensor.wo_de_jia_xuan_yi_distance') | round(2) }} km",
                  "{{ states('sensor.xuan_yi_che_liang_zhuang_tai') }} · 电瓶 "
                  "{{ states('sensor.xuan_yi_dian_chi_dian_ya') }}V",
                  'mdi:car',
                  '#FFD54F',  # 轩逸·黄（车辆身份色，与中控一致）
                  'sensor.wo_de_jia_xuan_yi_distance', tap='navigate'),
        tmpl_card("比亚迪 · {{ states('sensor.wo_de_jia_bi_ya_di_distance') | round(2) }} km",
                  "剩 {{ states('sensor.byd_yuan_sheng_yu_dian_liang') }}% · 续航 "
                  "{{ states('sensor.byd_yuan_sheng_yu_xu_hang') }}km",
                  'mdi:car-electric',
                  '#FF7AB6',  # 比亚迪·粉（车辆身份色，与中控一致）
                  'sensor.wo_de_jia_bi_ya_di_distance', tap='navigate'),
    ]
    cars_b = [
        tmpl_card("电动车",
                  "{{ states('sensor.wo_de_jia_dian_dong_che_distance') | round(2) }} km",
                  'mdi:moped',
                  '#59D98B',  # 电动车·绿（用户 11-05）
                  'sensor.wo_de_jia_dian_dong_che_distance', tap='navigate'),
        tmpl_card("{{ states('sensor.zhi_hui_ting_che_che_liang_xin_xi') }}",
                  "钱包 ¥{{ states('sensor.zhi_hui_ting_che_qian_bao_yu_e') }}",
                  'mdi:parking', C_MONEY, 'sensor.zhi_hui_ting_che_che_liang_xin_xi',
                  tap='more-info'),
    ]
    for c in (cars_a[0], cars_a[1], cars_b[0]):
        c['icon_tap_action'] = {'action': 'navigate', 'navigation_path': '/gaode_maps'}

    # 原「家居」的活动雷达 + 语音播报（用户指定与手机位对调）
    phones = [
        tmpl_card('{{ states("sensor.huo_dong_gui_ji") }}',
                  "{% set t = state_attr('sensor.huo_dong_gui_ji','motion_time') %}"
                  "{{ t | as_timestamp | timestamp_custom('%H:%M') if t else '最近没有走动' }}",
                  'mdi:radar',
                  cg("not is_state('sensor.huo_dong_gui_ji','未活动')"),
                  'sensor.huo_dong_gui_ji'),
        tmpl_card('扫地机',
                  "{% set vm = " + VACUUM_MAP + " %}"
                  "{{ vm.get(states('vacuum.ding_dang'), states('vacuum.ding_dang')) }} · "
                  "{% set fm = {'quiet':'安静','normal':'标准','max':'强力','max_plus':'超强'} %}"
                  "{{ fm.get(state_attr('vacuum.ding_dang','fan_speed'), state_attr('vacuum.ding_dang','fan_speed')) }}",
                  'mdi:robot-vacuum',
                  "{{ '" + C_BAD + "' if is_state('vacuum.ding_dang','error') else "
                  "('" + C_RUN + "' if is_state('vacuum.ding_dang','cleaning') else '" + C_OFF + "') }}",
                  'vacuum.ding_dang', tap='more-info'),
    ]

    info = html(
        "<div style=\"font-size:12.5px;line-height:1.55;opacity:.8\">"
        "{{ state_attr('sensor.gong_gong_xin_xi','fund').digest | replace('\\n','<br>') }}<br>"
        "{{ state_attr('sensor.gong_gong_xin_xi','term').digest | replace('\\n','<br>') }}<br>"
        "{{ state_attr('sensor.gong_gong_xin_xi','other').digest | replace('\\n','<br>') }}"
        "</div>", pad='2px 6px')

    return dict(title='此刻', path='phone', type='custom:vertical-layout',
         layout={'max_cols': 1}, cards=[
        head,
        section('动态', C_LINK, [info], cols=1, icon='mdi:newspaper-variant-outline'),
        section('家居', C_ON, home, 2, icon='mdi:home-outline'),
        section('车辆', C_NUM, cars_a, 1, icon='mdi:car-outline'),
        section('快捷', C_RUN, quick, 2, icon='mdi:gesture-tap-button'),
        section('安防', C_BAD, [security], cols=1, icon='mdi:shield-home-outline'),
        section('能耗', C_MONEY, today, 2, icon='mdi:lightning-bolt'),
        section('活动', C_NUM, cars_b + phones, 2, icon='mdi:radar'),
    ])


# ---------------------------------------------------------------- 视图 2 房间

def room_card(r, compact=False, accent='#5AA9FF'):
    sub_bits = []
    if r['temp']:
        sub_bits.append(
            "{% set t = states('" + r['temp'] + "') %}"
            "{{ (t | round(1) ~ '°C') if t not in ['unknown','unavailable'] else '--°C' }}")
        sub_bits.append(
            "{% set h = states('" + r['hum'] + "') %}"
            "{{ (h | round(0) | int ~ '%') if h not in ['unknown','unavailable'] else '--%' }}")
    elif r['light']:
        sub_bits.append("灯光 {{ (state_attr('" + r['light'] + "','entity_id') or ['.']) | count }} 路")
    # 人在状态放房间名后面（用户 11-05 指定）；门开/门关删掉，门窗状态看安防页
    # 标题行用 HTML 自绘：图标+房名加粗且同色条色，「无人/有人」保持普通样式
    # （用户 11-05 16:07 指定：加粗/变色只作用于 图标+房名）
    status = (" · {{ '有人' if is_state('" + r['motion'] + "','on') else '无人' }}"
              if r['motion'] else '')
    head = html(
        '<div style="display:flex;align-items:center;gap:9px">'
        '<ha-icon icon="' + r['icon'] + '" style="color:' + accent +
        ';--mdc-icon-size:28px;flex:none"></ha-icon>'
        '<div style="min-width:0">'
        '<div style="font-size:15px;line-height:18px;white-space:nowrap">'
        '<span style="font-weight:700;color:' + accent + '">' + r['name'] + '</span>'
        '<span style="font-size:12.5px;font-weight:400">' + status + '</span></div>'
        + ('<div style="font-size:11.5px;line-height:13px;opacity:.65">'
           + " · ".join(sub_bits) + '</div>' if sub_bits else '')
        + '</div></div>', pad='5px 9px')
    btns = []
    if r['light']:
        btns.append(tmpl_card(
            '灯·{{ (state_attr(\'' + r['light'] + '\',\'entity_id\') or [\'.\']) | count }}',
            "{{ '打开' if is_state('" + r['light'] + "','on') else '关闭' }}",
            'mdi:lightbulb-group', AMBER_GREY % r['light'], r['light'], tap='toggle',
            dense=True, pad='4px 6px', isize='22px'))
    if r['cover']:
        btns.append(tmpl_card(
            '窗帘', "{{ '关闭' if is_state('" + r['cover'] + "','closed') else '打开' }}",
            'mdi:curtains',
            "{{ '" + C_CURT + "' if not is_state('" + r['cover'] + "','closed') else '" + C_OFF + "' }}",
            r['cover'], tap='toggle', dense=True, pad='4px 6px', isize='22px'))
    if r['climate']:
        cmap = repr(CLIMATE_MAP)
        btns.append(tmpl_card(
            '空调',
            "{% set m = " + cmap + " %}{{ m.get(states('" + r['climate'] + "'), states('" + r['climate'] + "')) }}",
            'mdi:air-conditioner',
            "{{ '" + C_RUN + "' if not is_state('" + r['climate'] + "','off') else '" + C_OFF + "' }}",
            r['climate'], tap='more-info', dense=True, pad='4px 6px', isize='22px'))
    if not btns:
        btns.append(tmpl_card('门磁', "{{ '开' if is_state('" + r['doors'][0] + "','on') else '关' }}",
                              'mdi:door', 'grey', r['doors'][0], dense=True))
    if not btns:
        # 没有任何可控设备：只给一张带色条的卡
        st = head['card_mod']['style']
        body, tail = st.rsplit('}', 1)
        head['card_mod']['style'] = (body +
                                     '  background: ' + hexa(accent, .10) + ' !important;\n'
                                     '  border: 1px solid ' + hexa(accent, .42) + ' !important;\n'
                                     '  border-left: 5px solid ' + accent + ' !important;\n'
                                     '  border-radius: 12px !important;\n' + tail)
        return head
    # 单设备房间也只放一行按钮；块内按钮并排（用户 11-05 澄清：垂直罗列只指页面级）
    return room_block(head, btns, accent)


def view_rooms():
    def n_ctrl(r):
        return sum(1 for k in ('light', 'cover', 'climate') if r[k])

    def accent_of(r):
        # 房间可自带 accent 覆盖（如公卫固定蓝），否则按序取色
        return r.get('accent') or ACCENTS[ROOMS.index(r) % len(ACCENTS)]

    cards = []
    big = [r for r in ROOMS if n_ctrl(r) > 1]
    small = [r for r in ROOMS if n_ctrl(r) <= 1]
    for r in big:
        cards.append(room_card(r, accent=accent_of(r)))
    if small:
        # 只有灯的房间：两列并排（块内保持并排，页面级已单列）
        cards.append(grid([room_card(r, compact=True, accent=accent_of(r))
                           for r in small], 2))
    return dict(title='房间', path='rooms', type='custom:vertical-layout',
         layout={'max_cols': 1}, cards=cards)


# ---------------------------------------------------------------- 视图 3 安防

def view_security():
    doors_expr = ", ".join(f"'{e}'" for _, e in DOORS)
    alarm_expr = ", ".join(f"'{e}'" for _, e, _, _ in ALARMS)
    summary = html(
        "<div style=\"font-size:14px;line-height:1.6\">"
        "{% set d = expand(" + doors_expr + ") %}"
        "{% set a = expand(" + alarm_expr + ") %}"
        "{% set dn = d | selectattr('state','eq','on') | list | count %}"
        "{% set an = a | selectattr('state','eq','on') | list | count %}"
        "{% if dn + an == 0 %}"
        "<span style=\"color:#59D98B;font-weight:600\">● 一切正常</span>"
        "<div style=\"font-size:12.5px;opacity:.65;margin-top:2px\">"
        "{{ d | count }} 处门 / 窗已闭合，{{ a | count }} 项环境告警无触发</div>"
        "{% else %}"
        "<span style=\"color:#FF5252;font-weight:600\">● {{ dn + an }} 处需要留意</span>"
        "<div style=\"font-size:12.5px;opacity:.65;margin-top:2px\">"
        "{% if dn %}门窗 {{ dn }} 处未关{% endif %}"
        "{% if an %} · 环境告警 {{ an }} 项{% endif %}</div>"
        "{% endif %}</div>", pad='8px 8px 6px')

    def sensor_card(label, eid, icon):
        return tmpl_card(
            label,
            "{{ '打开' if is_state('" + eid + "','on') else '关闭' }}",
            icon,
            "{{ 'red' if is_state('" + eid + "','on') else 'grey' }}",
            eid, tap='more-info')

    door_cards = [sensor_card(n, e, 'mdi:door-open') for n, e in DOORS]
    win_cards = [sensor_card(n, e, ic) for n, e, ic in WINDOWS]
    alarm_cards = [tmpl_card(
        n, "{{ '告警' if is_state('" + e + "','on') else '正常' }} · " + loc, ic,
        "{{ 'red' if is_state('" + e + "','on') else 'green' }}", e, tap='more-info')
        for n, e, ic, loc in ALARMS]

    def cam_card(name, eid):
        """不要图标，只报在线状态（在线绿 / 离线红）。"""
        st = ("{% set s = states('" + eid + "') %}"
              "{% set off = s in ['unavailable','unknown',''] %}"
              "{{ '离线' if off else '在线' }}")
        col = ("{% set s = states('" + eid + "') %}"
               "{{ '#FF5252' if s in ['unavailable','unknown',''] else '#59D98B' }}")
        card = html(
            '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;'
            'padding:9px 12px">'
            '<span style="font-size:13.5px">' + name + '</span>'
            '<span style="font-size:12.5px;color:' + col + '">' + st + '</span>'
            '</div>', pad='0')
        return card

    cams = [cam_card('大门监控', 'camera.da_men_jian_kong'),
            cam_card('后门监控', 'camera.hou_men_jian_kong')]

    # 顺序（用户指定）：监控 → 环境告警 → 窗·帘 → 门（门放最后）
    # summary 是「门 + 环境告警」的合计，属于安防总提示 → 放最前端
    return dict(title='安防', path='security', type='custom:vertical-layout',
         layout={'max_cols': 1}, cards=[
        section('总概', C_BAD, [summary], 1, icon='mdi:clipboard-list-outline'),
        section('监控', C_LINK, cams, 2, icon='mdi:cctv'),
        section('环境', C_MONEY, alarm_cards, 2, icon='mdi:smoke-detector'),
        section('窗 · 帘', C_NUM, win_cards, 2, note=str(len(WINDOWS)) + ' 处', icon='mdi:curtains'),
        section('门', C_ON, door_cards, 2, note=str(len(DOORS)) + ' 处', icon='mdi:door-closed'),
    ])


# ---------------------------------------------------------------- 视图 4 能源

def view_energy():
    today = [
        tmpl_card('今日电费', "¥ {{ states('sensor.jin_ri_dian_fei') }}", 'mdi:currency-cny', C_MONEY,
                  'sensor.jin_ri_dian_fei'),
        tmpl_card('今日用电', "{{ states('sensor.tasmota_energy_today') | round(2) }} 度", 'mdi:flash',
                  C_MONEY, 'sensor.tasmota_energy_today'),
        tmpl_card('今日用水', "{{ states('sensor.maze_wateronev3_tp_f8e644_daily_water_usage') | round(1) }} L",
                  'mdi:water', C_LINK, 'sensor.maze_wateronev3_tp_f8e644_daily_water_usage'),
        tmpl_card('今日用气', "{{ states('sensor.ri_yong_qi_liang') }} m³", 'mdi:fire', C_ON,
                  'sensor.ri_yong_qi_liang'),
    ]

    month = [
        tmpl_card('本月电费', "¥ {{ states('sensor.ben_yue_dian_fei') }}", 'mdi:calendar-month', C_MONEY,
                  'sensor.ben_yue_dian_fei'),
        tmpl_card('本月用电', "{{ states('sensor.yue_yong_dian_liang') | round(1) }} 度", 'mdi:meter-electric',
                  C_MONEY, 'sensor.yue_yong_dian_liang'),
        tmpl_card('昨日电费', "¥ {{ states('sensor.zuo_ri_dian_fei') }}", 'mdi:history', C_NUM,
                  'sensor.zuo_ri_dian_fei'),
        tmpl_card('实时电价', "¥ {{ states('sensor.shi_shi_dian_jie') }} /度", 'mdi:tag', C_NUM,
                  'sensor.shi_shi_dian_jie'),
    ]

    power = {
        'type': 'custom:mini-graph-card',
        'hours_to_show': 24,
        'points_per_hour': 2,
        'line_width': 2,
        'font_size': 80,
        # 图例（智能电表 功率/厨房/机柜字样）整行隐藏（用户 11-05 指定）
        'show': {'legend': False},
        'entities': [
            {'entity': 'sensor.tasmota_energy_power'},
            {'entity': 'sensor.kitchen_total_power', 'name': '厨房'},
            {'entity': 'sensor.e84a54643016_power', 'name': '机柜'},
        ],
    }

    elec = [
        tmpl_card('电压', "{{ states('sensor.tasmota_energy_voltage') }} V", 'mdi:sine-wave', C_RUN,
                  'sensor.tasmota_energy_voltage'),
        tmpl_card('电流', "{{ states('sensor.tasmota_energy_current') | round(1) }} A", 'mdi:current-ac',
                  C_RUN, 'sensor.tasmota_energy_current'),
    ]

    water = [
        tmpl_card('水压', "{{ states('sensor.maze_wateronev3_tp_f8e644') | round(2) }} bar", 'mdi:gauge', C_LINK,
                  'sensor.maze_wateronev3_tp_f8e644'),
        tmpl_card('水温', "{{ states('sensor.maze_wateronev3_tp_f8e644_tds') }}°C", 'mdi:thermometer-water',
                  C_LINK, 'sensor.maze_wateronev3_tp_f8e644_tds'),
        tmpl_card('进水 TDS', "{{ states('sensor.maze_wateronev3_tp_f8e644_tdsin') }} ppm", 'mdi:water-opacity',
                  C_NUM, 'sensor.maze_wateronev3_tp_f8e644_tdsin'),
        tmpl_card('出水 TDS', "{{ states('sensor.maze_wateronev3_tp_f8e644_tdsout') }} ppm", 'mdi:water-check',
                  C_OK, 'sensor.maze_wateronev3_tp_f8e644_tdsout'),
    ]

    ac = [
        tmpl_card('客厅空调', "{{ states('sensor.208907215082288_realtime_power') }} W", 'mdi:air-conditioner',
                  C_RUN, 'sensor.208907215082288_realtime_power'),
        tmpl_card('主卧空调', "{{ states('sensor.208907213270301_realtime_power') }} W", 'mdi:air-conditioner',
                  C_RUN, 'sensor.208907213270301_realtime_power'),
        tmpl_card('次卧空调', "{{ states('sensor.210006724901473_realtime_power') }} W", 'mdi:air-conditioner',
                  C_RUN, 'sensor.210006724901473_realtime_power'),
        tmpl_card('书房空调', "{{ states('sensor.210006724901502_realtime_power') }} W", 'mdi:air-conditioner',
                  C_RUN, 'sensor.210006724901502_realtime_power'),
    ]

    fee = html(
        "<div style=\"font-size:12.5px;line-height:1.7;opacity:.8\">"
        "{{ state_attr('sensor.fei_yong_gai_kuang','message1') }}"
        "</div>", pad='6px 6px')

    # 余额概况（用户 11-05 指定加一段【余额】）
    bal = html(
        "<div style=\"font-size:12.5px;line-height:1.7;opacity:.8\">"
        "{{ state_attr('sensor.yu_e_fei_yong_gai_kuang','balance_detail') }}"
        "</div>", pad='6px 6px')

    # 费用总览放最上面（用户指定），一眼看到本月合计；余额并入本块（用户 11-05 指定）
    return dict(title='能源', path='energy', type='custom:vertical-layout',
                layout={'max_cols': 1}, cards=[
        section('费用总览', C_MONEY, [fee, bal], cols=1, icon='mdi:cash-multiple'),
        section('今日能耗', C_ON, today, 2, icon='mdi:flash'),
        section('本月费用', C_NUM, month, 2, icon='mdi:chart-bar'),
        section('功率趋势', C_OK, [power], cols=1, icon='mdi:chart-line'),
        section('电气', C_RUN, elec, 2, icon='mdi:power-plug-outline'),
        section('净水', C_LINK, water, 2, icon='mdi:water-outline'),
        section('空调', C_RUN, ac, 2, icon='mdi:air-conditioner'),
    ])


# ---------------------------------------------------------------- 输出

class Dumper(yaml.SafeDumper):
    """让 Jinja 模板在 YAML 里保持可读（HTML 用块标量，模板用双引号）"""


def _str_rep(dumper, data):
    style = None
    if '\n' in data or '"' in data:
        style = '|'
    elif "'" in data or '{{' in data or '{%' in data:
        style = '"'
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


Dumper.add_representer(str, _str_rep)


def main():
    views = [view_now(), view_energy(), view_rooms(), view_security()]
    if VIEW_VISIBLE:
        for v in views:
            v['visible'] = [dict(u) for u in VIEW_VISIBLE]   # 每视图独立副本，避免 yaml 锚点 &id001
    cfg = {
        'title': '掌控',
        'views': views,
    }
    head = ("# 掌控 —— 手机优先的全屋操作台\n"
            "# 与「概览」（桌面四栏全景）、「屏幕镜像」（墙屏 1:1 复刻）分工互补。\n"
            "# 依赖：mushroom / stack-in-card / mini-graph-card / html-template-card / webrtc-camera（均已安装）\n"
            "# 生成：python case/scripts/gen_control_panel.py —— 手改请同时改生成器\n\n")
    body = yaml.dump(cfg, Dumper=Dumper, allow_unicode=True, sort_keys=False,
                     width=10000, indent=1)
    # 输出直接写 HA Lovelace 界面工作区（用户 11-05 将界面成品平移到 D:\HA Lovelace）
    out = os.path.join('..', 'HA Lovelace', 'lovelace', 'lovelace_phone_dashboard.yaml')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(head + body)
    print(f'✓ 已生成 {out}  '
          f'（{len(cfg["views"])} 视图 / {sum(len(v["cards"]) for v in cfg["views"])} 顶层卡片）')
    for v in cfg['views']:
        print(f'   {v["title"]:4} /{v["path"]:9} {len(v["cards"])} 卡')


if __name__ == '__main__':
    main()
