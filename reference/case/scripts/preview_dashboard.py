# -*- coding: utf-8 -*-
"""「中控」页面本地预览：拉 HA 真实状态，jinja2 模拟 HA 模板函数渲染，Chrome 截图。

用法：python preview_dashboard.py [输出.png]
产物：.workbuddy/dash_preview.html + PNG（1280×800 逻辑 @2x）
"""
import base64
import io
import json
import os
import subprocess
import sys
import urllib.request

import jinja2
import yaml

ROOT = r'D:\HA Lovelace'
HA_SCRIPTS = r'D:\HA Monitor Display'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
WB = os.path.join(ROOT, '.workbuddy')


def ha_states():
    tok = io.open(os.path.join(HA_SCRIPTS, '.workbuddy', 'ha_token.txt'),
                  encoding='utf-8').read().strip()
    req = urllib.request.Request('http://192.168.1.125:8123/api/states',
                                 headers={'Authorization': 'Bearer ' + tok})
    return {s['entity_id']: s for s in json.load(urllib.request.urlopen(req))}


def render(content, st):
    env = jinja2.Environment()

    def _round(v, n=0):
        try:
            return round(float(v), int(n))
        except (TypeError, ValueError):
            return v
    env.filters['round'] = _round

    def states(eid=None):
        if eid is None:
            return ''
        s = st.get(eid)
        return s['state'] if s else 'unknown'

    def is_state(eid, val):
        return states(eid) == val

    def state_attr(eid, attr=None):
        s = st.get(eid)
        if not s:
            return None
        return s['attributes'] if attr is None else s['attributes'].get(attr)

    def expand(eids):
        return [{'entity_id': e, 'state': states(e)} for e in eids]

    return env.from_string(content).render(states=states, is_state=is_state,
                                           state_attr=state_attr, expand=expand)


def ha_check(content):
    """用 HA /api/template 真实校验（本地模拟器发现不了 HA 特有限制）。"""
    tok = io.open(os.path.join(HA_SCRIPTS, '.workbuddy', 'ha_token.txt'),
                  encoding='utf-8').read().strip()
    req = urllib.request.Request(
        'http://192.168.1.125:8123/api/template',
        data=json.dumps({'template': content}).encode(),
        headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=30)
        print('✓ HA 模板校验通过')
    except urllib.error.HTTPError as e:
        raise SystemExit('HA 模板渲染失败: ' + e.read().decode()[:800])


def main():
    png = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WB, 'dash_preview.png')
    cfg = yaml.safe_load(io.open(os.path.join(ROOT, 'lovelace', 'lovelace_tablet_dashboard.yaml'),
                                 encoding='utf-8').read())
    content = cfg['views'][0]['cards'][0]['content']
    ha_check(content)
    mdi_css = os.path.join(WB, 'mdifont', 'mdi.css').replace('\\', '/')
    css = io.open(mdi_css, encoding='utf-8').read()
    woff = base64.b64encode(open(os.path.join(WB, 'mdifont', 'mdi.woff2'), 'rb').read()).decode()
    css = css.replace('mdi.woff2', 'data:font/woff2;base64,' + woff)
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<style>' + css + '</style>'
            '<style>html,body{margin:0;background:#0A0D0B;overflow:hidden}</style></head><body>'
            + render(content, ha_states()) + '</body></html>')
    hf = os.path.join(WB, 'dash_preview.html')
    io.open(hf, 'w', encoding='utf-8').write(html)
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    '--force-device-scale-factor=2', '--window-size=1280,800',
                    '--screenshot=' + png, 'file:///' + hf.replace('\\', '/')],
                   check=True, capture_output=True)
    print('✓ 预览 ->', png)


if __name__ == '__main__':
    main()
