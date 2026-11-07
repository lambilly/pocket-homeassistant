# -*- coding: utf-8 -*-
"""把 lovelace YAML 渲染成手机预览 HTML（给用户确认用，不接触 HA）。

用法：python case/scripts/preview_control_panel.py
产物：tools/control-panel-preview.html
"""
import datetime
import io
import json
import math
import os
import re
import sys
import urllib.request

import yaml
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hmd_jinja import build_env  # noqa: E402

YAML_PATH = sys.argv[1] if len(sys.argv) > 1 else 'HA Lovelace/lovelace/lovelace_phone_dashboard.yaml'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'tools/control-panel-preview.html'
ONLY = int(sys.argv[3]) if len(sys.argv) > 3 else None   # 只渲染某一个视图（1 起），截图用
MDI_TTF = 'fonts/materialdesignicons-webfont.ttf'
MDI_CACHE = '.workbuddy/mdi_map.json'

COLORS = {
    'red': '#f44336', 'pink': '#e91e63', 'purple': '#9c27b0', 'deep-purple': '#673ab7',
    'indigo': '#3f51b5', 'blue': '#2196f3', 'light-blue': '#03a9f4', 'cyan': '#00bcd4',
    'teal': '#009688', 'green': '#4caf50', 'light-green': '#8bc34a', 'lime': '#cddc39',
    'yellow': '#ffeb3b', 'amber': '#ffc107', 'orange': '#ff9800', 'deep-orange': '#ff5722',
    'brown': '#795548', 'grey': '#9e9e9e', 'blue-grey': '#607d8b',
    'white': '#ffffff', 'black': '#000000', 'disabled': '#bdbdbd', '': 'var(--dim)',
}


def load_mdi():
    if os.path.exists(MDI_CACHE):
        return json.load(io.open(MDI_CACHE, encoding='utf-8'))
    f = TTFont(MDI_TTF)
    m = {name: '&#x%x;' % cp for cp, name in f.getBestCmap().items()}
    json.dump(m, io.open(MDI_CACHE, 'w', encoding='utf-8'))
    return m


MDI = load_mdi()
env, STATES = build_env()


def icon(mdi_name):
    if not mdi_name:
        return ''
    return MDI.get(mdi_name.replace('mdi:', ''), '&#x25cf;')


def _ha_icon(m):
    ic, style = m.group(1), (m.group(2) or '')
    size = 24
    ms = re.search(r'--mdc-icon-size:\s*([0-9.]+)px', style)
    if ms:
        size = float(ms.group(1))
    style = re.sub(r'--mdc-icon-size:[^;"]*;?', '', style)
    if style and not style.endswith(';'):
        style += ';'
    return (f'<span style="{style}font-family:MDI;font-size:{size}px;'
            f'line-height:1;display:inline-block">{icon(ic)}</span>')


def render(s):
    if not isinstance(s, str):
        return ''
    try:
        out = env.from_string(s).render()
    except Exception as e:
        return f'[模板错误 {e}]'
    # html 内容里的 ha-icon 换成 MDI 字体字形（真机由 HA 前端渲染）
    out = re.sub(r'<ha-icon icon="(mdi:[^"]+)"(?:\s+style="([^"]*)")?\s*/?>\s*(?:</ha-icon>)?',
                 _ha_icon, out)
    return out.strip()


def hexa(color, alpha):
    c = color.lstrip('#')
    if len(c) == 3:
        c = ''.join(x * 2 for x in c)
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def resolve_color(v):
    v = (v or '').strip().strip('"')
    if v.startswith('#'):
        return v
    return COLORS.get(v, 'var(--dim)')


# ---------------------------------------------------------------- 历史曲线

def fetch_power():
    try:
        token = io.open('.workbuddy/ha_token.txt', encoding='utf-8').read().strip()
        start = (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
        ids = 'sensor.tasmota_energy_power,sensor.kitchen_total_power,sensor.e84a54643016_power'
        url = (f'http://192.168.1.125:8123/api/history/period/{start}'
               f'?filter_entity_id={ids}&minimal_response&no_attributes')
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        raw = json.load(urllib.request.urlopen(req, timeout=25))
        out = []
        for series in raw:
            pts = []
            for p in series:
                try:
                    pts.append(max(0.0, float(p['state'])))
                except (TypeError, ValueError, KeyError):
                    pass
            out.append(pts)
        if all(len(p) > 10 for p in out):
            json.dump(out, io.open('.workbuddy/history_power.json', 'w'))
            return out
    except Exception as e:
        print('  历史数据取不到，用示意曲线:', e)
    if os.path.exists('.workbuddy/history_power.json'):
        return json.load(io.open('.workbuddy/history_power.json'))
    return [[200 + 120 * math.sin(i / 14) + 40 * math.sin(i / 3) for i in range(160)] for _ in range(3)]


# ---------------------------------------------------------------- 卡片渲染

def card_html(n):
    t = n.get('type', '')
    if t == 'custom:mushroom-template-card':
        col = resolve_color(render(n.get('color', '')))
        primary = render(n.get('primary', ''))
        secondary = render(n.get('secondary', ''))
        vertical = n.get('vertical')
        st = (n.get('card_mod') or {}).get('style') or ''

        def g(prop, default):
            m = re.search(re.escape(prop) + r':\s*([0-9.]+px)', st)
            return m.group(1) if m else default

        pf = g('--mush-card-primary-font-size', '13.5px')
        pl = g('--mush-card-primary-line-height', '17px')
        sf = g('--mush-card-secondary-font-size', '11.5px')
        sl = g('--mush-card-secondary-line-height', '14px')
        ico = g('--mush-icon-size', '34px')
        pm = re.search(r'padding:[ \t]*([0-9.]+px[ \t]+[0-9.]+px)', st)
        pad = pm.group(1) if pm else '8px 10px'
        isz = float(ico[:-2])
        fs = round(isz * 0.56, 1)
        cls = 'mc v' if vertical else 'mc'
        am = re.search(r'border-left:[ \t]*[0-9.]+px solid (#[0-9A-Fa-f]{6})', st)
        if am:
            acc = am.group(1)
            cls += ' room1'
            extra = (f'border:1px solid {hexa(acc, .42)};border-left:5px solid {acc};'
                     f'background:{hexa(acc, .10)};border-radius:12px;')
            pcol = f'color:{acc};font-weight:600;'
        else:
            extra = ''
            pcol = ''
        return (f'<div class="{cls}" style="padding:{pad};{extra}">'
                f'<div class="ic" style="color:{col};background:{hexa(col, .13)}'
                f';width:{ico};height:{ico};font-size:{fs}px">'
                f'{icon(n.get("icon"))}</div>'
                f'<div class="tx"><div class="p" style="font-size:{pf};line-height:{pl};{pcol}">'
                f'{primary}</div>'
                + (f'<div class="s" style="font-size:{sf};line-height:{sl}">{secondary}</div>'
                   if secondary else '')
                + '</div></div>')
    if t == 'custom:html-template-card':
        return '<div class="html">' + render(n.get('content', '')) + '</div>'
    if t == 'grid':
        cols = n.get('columns', 2)
        inner = ''.join(card_html(c) for c in n.get('cards', []))
        return f'<div class="g" style="grid-template-columns:repeat({cols},1fr)">{inner}</div>'
    if t == 'custom:stack-in-card':
        inner = ''.join(card_html(c) for c in n.get('cards', []))
        st = (n.get('card_mod') or {}).get('style') or ''
        am = re.search(r'border-left:[ \t]*[0-9.]+px solid (#[0-9A-Fa-f]{6})', st)
        if am:
            acc = am.group(1)
            return (f'<div class="stk room" style="--acc:{acc};'
                    f'border:1px solid {hexa(acc, .42)};border-left:5px solid {acc}">'
                    f'{inner}</div>')
        return f'<div class="stk">{inner}</div>'
    if t == 'custom:mini-graph-card':
        return graph_html(n)
    if t == 'custom:webrtc-camera':
        eid = n.get('entity') or ''
        nm = (STATES.get(eid, {}).get('attributes') or {}).get('friendly_name', '摄像头')
        return (f'<div class="cam"><div class="camic">{icon("mdi:video")}</div>'
                f'<div class="camtx">{nm}<span>RTSP 实时画面</span></div></div>')
    return f'<div class="mc"><div class="tx"><div class="p">[{t}]</div></div></div>'


def graph_html(n):
    series = fetch_power()
    names = [e.get('name', '') for e in n.get('entities', [])]
    colors = ['#ff9f09', '#4fd8fa', '#59d98b']
    W, H = 320, 96
    mx = max(max(s) for s in series) or 1
    paths = []
    for i, s in enumerate(series):
        step = max(1, len(s) // 90)
        pts = s[::step]
        mx = max(mx, max(pts) or 1)
    for i, s in enumerate(series):
        step = max(1, len(s) // 90)
        pts = s[::step]
        d = ' '.join(f'{"M" if k == 0 else "L"}{k * W / max(1, len(pts) - 1):.1f},'
                     f'{H - (v / mx * (H - 8)) - 4:.1f}' for k, v in enumerate(pts))
        paths.append(f'<path d="{d}" fill="none" stroke="{colors[i % 3]}" stroke-width="1.8"/>')
    legend = ''.join(f'<span><i style="background:{colors[i % 3]}"></i>{nm}</span>'
                     for i, nm in enumerate(names))
    return (f'<div class="mc graph"><div class="gt">{n.get("name", "功率")}'
            f'<b>峰值 {mx:.0f} W</b></div>'
            f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none">{"".join(paths)}</svg>'
            f'<div class="gl">{legend}</div></div>')


# ---------------------------------------------------------------- 页面

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0b0d;color:#fff;font-family:-apple-system,"PingFang SC","Segoe UI",Roboto,sans-serif;
  padding:26px 26px 60px;-webkit-font-smoothing:antialiased}
.top{max-width:1700px;margin:0 auto 20px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.top h1{font-size:19px;font-weight:600;letter-spacing:.3px}
.top p{font-size:13px;color:rgba(255,255,255,.52)}
.rail{display:flex;gap:22px;overflow-x:auto;padding-bottom:18px;max-width:2450px;margin:0 auto}
.phone{flex:0 0 392px;width:392px;border-radius:34px;overflow:hidden;position:relative;
  border:1px solid rgba(255,255,255,.14);box-shadow:0 22px 54px rgba(0,0,0,.6);background:#151517}
.wall{position:absolute;inset:0;
  background:
   radial-gradient(80% 55% at 15% 5%,rgba(255,159,9,.16),transparent 60%),
   radial-gradient(70% 50% at 90% 25%,rgba(79,216,250,.13),transparent 62%),
   radial-gradient(90% 60% at 50% 100%,rgba(120,80,255,.16),transparent 65%),
   linear-gradient(170deg,#191a1e,#101013 55%,#17161a)}
.inner{position:relative;padding:0 10px 34px}
.sbar{height:26px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;
  font-size:10.5px;color:rgba(255,255,255,.72);padding-top:5px}
.hd{display:flex;align-items:center;gap:9px;padding:5px 6px 8px;color:#fff}
.hd .ttl{font-size:14.5px;font-weight:600}
.hd .menu{font-size:17px;opacity:.7}
.tabs{display:flex;gap:16px;padding:0 8px 10px;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{font-size:14px;font-weight:500;color:rgba(255,255,255,.55);white-space:nowrap;
  display:flex;align-items:center;gap:5px;padding-bottom:4px}
.tab.on{color:#fff;box-shadow:inset 0 -2px 0 #ff9f09}
.tab i{font-size:16px;font-style:normal}
.mc{background:rgba(10,10,10,.44);border:1px solid rgba(255,255,255,.075);border-radius:12px;
  padding:8px 10px;display:flex;align-items:center;gap:9px;backdrop-filter:blur(10px)}
.mc.v{flex-direction:column;align-items:center;text-align:center;gap:5px;padding:10px 7px}
.mc .ic{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;
  font-size:19px;flex:0 0 auto;line-height:1;font-family:"MDI"}
.mc.d{padding:7px 8px;gap:7px}
.mc.d .ic{width:28px;height:28px;font-size:16px}
.mc.d .p{font-size:12.5px;line-height:16px}
.mc.d .s{font-size:11px;line-height:13px}
.mc.v .ic{width:34px;height:34px;font-size:19px}
.mc .tx{min-width:0;flex:1}
.mc.v .tx{flex:none;width:100%}
.mc .p{font-size:13.5px;font-weight:500;line-height:17px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.mc.v .p{font-size:13px;white-space:normal}
.mc .s{font-size:11.5px;color:rgba(255,255,255,.6);line-height:14px;margin-top:0;
  white-space:pre-line;word-break:break-word}
.g{display:grid;gap:8px}
.stk{background:rgba(12,12,14,.62);border:1px solid rgba(255,255,255,.15);border-radius:14px;
  overflow:hidden;padding:4px;display:flex;flex-direction:column;gap:3px}
.stk.room{background:rgba(14,14,16,.86);box-shadow:0 2px 10px rgba(0,0,0,.28);padding:4px 4px 5px}
.stk .mc{background:rgba(28,28,30,.72);border:1px solid rgba(255,255,255,.10);border-radius:12px}
.stk .html:not(:first-child){background:rgba(28,28,30,.72);
  border:1px solid rgba(255,255,255,.10);border-radius:12px}
.stk.room > .mc:first-child{background:linear-gradient(90deg,
  color-mix(in srgb, var(--acc) 26%, transparent),
  color-mix(in srgb, var(--acc) 6%, transparent) 70%, transparent) !important;
  box-shadow:inset 0 -1px 0 color-mix(in srgb, var(--acc) 55%, transparent)}
.stk.room > .mc:first-child .p{color:var(--acc) !important;font-weight:600}
.stk.room > .html:first-child{background:linear-gradient(90deg,
  color-mix(in srgb, var(--acc) 26%, transparent),
  color-mix(in srgb, var(--acc) 6%, transparent) 70%, transparent);
  box-shadow:inset 0 -1px 0 color-mix(in srgb, var(--acc) 55%, transparent)}
.stk.room > .html{padding:0}
.stk.room > .g{padding:0 2px 2px}
.stk .mc{border-radius:10px}
.html{padding:2px 2px}
.cam{aspect-ratio:16/10;border-radius:12px;background:linear-gradient(160deg,#232326,#141416);
  border:1px solid rgba(255,255,255,.08);display:grid;place-items:center;position:relative}
.camic{font-family:"MDI";font-size:34px;color:rgba(255,255,255,.28)}
.camtx{position:absolute;left:10px;bottom:8px;font-size:11.5px;color:rgba(255,255,255,.66);
  display:flex;gap:7px;align-items:center}
.camtx span{font-size:10px;opacity:.55}
.graph{flex-direction:column;align-items:stretch;gap:7px}
.gt{display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,.72)}
.gt b{font-weight:500;color:rgba(255,255,255,.5)}
.graph svg{width:100%;height:74px;display:block}
.gl{display:flex;gap:12px;font-size:10.5px;color:rgba(255,255,255,.55)}
.gl i{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px}
.gap{height:8px}
"""


def main():
    cfg = yaml.safe_load(io.open(YAML_PATH, encoding='utf-8'))
    views = cfg['views']
    if ONLY:
        views = views[ONLY - 1:ONLY]
    nav = ''.join(
        f'<span class="tab{"" if i else " on"}"><i>{icon(v.get("icon"))}</i>{v["title"]}</span>'
        for i, v in enumerate(views))
    tabs_all = f'<div class="tabs">{nav}</div>'

    phones = []
    for vi, v in enumerate(views):
        vi = 0 if ONLY else vi
        nav = ''.join(
            f'<span class="tab{" on" if i == vi else ""}">'
            f'<i>{icon(x.get("icon"))}</i>{x["title"]}</span>'
            for i, x in enumerate(views))
        body = ''.join(card_html(c) + ('' if c.get('type') in ('grid', 'custom:stack-in-card', 'custom:html-template-card') else '<div class="gap"></div>')
                       for c in v['cards'])
        phones.append(
            '<section class="phone"><div class="wall"></div><div class="inner">'
            '<div class="sbar"><span>23:41</span><span>5G ▮▮▮ 86%</span></div>'
            '<div class="hd"><span class="menu">☰</span><span class="ttl">掌控</span></div>'
            f'<div class="tabs">{nav}</div>{body}</div></section>')

    html = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>掌控 · 面板预览</title>'
            f'<style>@font-face{{font-family:"MDI";src:url("../fonts/materialdesignicons-webfont.ttf") '
            f'format("truetype")}}{CSS}</style></head><body>'
            '<div class="top"><h1>掌控</h1>'
            f'<p>手机优先的全屋操作台 · 真实数据渲染 · {len(views)} 个视图</p></div>'
            '<div class="rail">' + ''.join(phones) + '</div></body></html>')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print(f'✓ 预览已生成 {OUT}')


if __name__ == '__main__':
    main()
