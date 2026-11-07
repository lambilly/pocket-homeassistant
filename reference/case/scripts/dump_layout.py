"""把 ui/page_*.yaml 的控件树导成 JSON（含绝对坐标），用于网页 1:1 复刻。
用法：cd "D:/HA Monitor Display" && python case/scripts/dump_layout.py > out.json
"""
import yaml, io, re, json, sys

FILES = {
    'dashboard': 'ui/page_dashboard.yaml',
    'network': 'ui/page_network.yaml',
    'system': 'ui/page_system.yaml',
    'notify': 'ui/page_notify.yaml',
}

WID = ('obj', 'label', 'button', 'image', 'bar', 'slider', 'switch')


def walk(ws, ox=0, oy=0):
    out = []
    for w in ws or []:
        if not isinstance(w, dict):
            continue
        for k, v in w.items():
            if k not in WID or not isinstance(v, dict):
                continue
            x = ox + (v.get('x') or 0)
            y = oy + (v.get('y') or 0)
            node = {
                'type': k,
                'x': x, 'y': y,
                'w': v.get('width'), 'h': v.get('height'),
                'id': v.get('id'),
                'align': v.get('align'),
                'text': v.get('text'),
                'font': v.get('text_font'),
                'color': v.get('text_color'),
                'bg': v.get('bg_color'),
                'border': v.get('border_color'),
                'bw': v.get('border_width'),
                'radius': v.get('radius'),
                'bg_opa': v.get('bg_opa'),
            }
            ch = walk(v.get('widgets'), x, y)
            if ch:
                node['children'] = ch
            out.append({k: node})
    return out


res = {}
for name, fn in FILES.items():
    s = io.open(fn, encoding='utf-8').read()
    s = re.sub(r'^(\s*)- !include .*$', r'\1- {}\n  # include skipped', s, flags=re.M)
    d = yaml.safe_load(s)
    pg = d['lvgl']['pages'][0]
    res[name] = {
        'w': pg.get('width'), 'h': pg.get('height'),
        'bg': pg.get('bg_color'),
        'tree': walk(pg['widgets']),
    }

json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
