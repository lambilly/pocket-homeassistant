"""校验「掌控」面板：实体存在性 + Jinja 模板可渲染 + 结构合法。
用法：python case/scripts/verify_control_panel.py [yaml路径]
"""
import io
import json
import re
import sys

import yaml
from jinja2 import Environment

YAML = sys.argv[1] if len(sys.argv) > 1 else 'HA Lovelace/lovelace/lovelace_phone_dashboard.yaml'
STATES = {e['entity_id']: e for e in json.load(io.open('.workbuddy/ha_states.json', encoding='utf-8'))}

# ---------------- 桩环境
def _states(eid):
    return STATES.get(eid, {}).get('state', 'unknown')

def _state_attr(eid, attr, default=None):
    v = (STATES.get(eid, {}).get('attributes') or {}).get(attr)
    return default if v is None else v

def _is_state(eid, val):
    s = _states(eid)
    return s == val if isinstance(val, str) else s in val

def _expand(*args):
    out = []
    for a in args:
        e = STATES.get(a)
        out.append({'entity_id': a, 'state': e['state'] if e else 'unknown'})
    return out

def _as_ts(v, default=0):
    if v in (None, '', 'unknown', 'unavailable'):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _ts_custom(value, fmt='%H:%M', local=True):
    import datetime
    if value in (None, ''):
        return ''
    return datetime.datetime.fromtimestamp(float(value)).strftime(fmt)

env = Environment(autoescape=False)
env.globals.update(states=_states, state_attr=_state_attr, is_state=_is_state,
                   expand=_expand, user='林宗华', now=lambda: __import__('datetime').datetime.now(),
                   as_timestamp=_as_ts)
env.filters.update(as_timestamp=_as_ts, timestamp_custom=_ts_custom,
                   float=lambda v, d=0: float(v) if str(v).replace('.', '', 1).lstrip('-').isdigit() else d,
                   int=lambda v, d=0: int(float(v)) if str(v).replace('.', '', 1).lstrip('-').isdigit() else d,
                   round=lambda v, p=0: round(float(v), p) if str(v).replace('.', '', 1).lstrip('-').isdigit() else v,
                   relative_time=lambda v: str(v))

cfg = yaml.safe_load(io.open(YAML, encoding='utf-8'))
src = io.open(YAML, encoding='utf-8').read()

# ---------------- 结构
print(f'标题: {cfg.get("title")}   视图: {len(cfg.get("views", []))}')
paths = [v.get('path') for v in cfg['views']]
assert len(set(paths)) == len(paths), f'视图 path 重复: {paths}'
print('视图:', ', '.join(f'{v["title"]}(/{v["path"]})' for v in cfg['views']))

# ---------------- 实体
EID = re.compile(r'\b((?:sensor|binary_sensor|switch|light|fan|climate|number|select|button|'
                 r'cover|media_player|vacuum|lock|camera|weather|person|zone|device_tracker)\.[a-z0-9_]+)')
refs = set(EID.findall(src))
# service 调用（climate.turn_off / light.toggle ...）不是实体
SERVICES = {'climate.turn_off', 'light.toggle', 'light.turn_off', 'light.turn_on',
            'cover.toggle', 'homeassistant.turn_off', 'homeassistant.turn_on'}
refs -= SERVICES
missing = sorted(r for r in refs if r not in STATES)
print(f'\n引用实体 {len(refs)} 个，缺失 {len(missing)}')

# ---------------- 模板渲染
tpl, bad = 0, []

def walk(n, path=''):
    global tpl
    if isinstance(n, list):
        for i, x in enumerate(n):
            walk(x, f'{path}[{i}]')
        return
    if not isinstance(n, dict):
        return
    for k, v in n.items():
        if isinstance(v, str) and ('{{' in v or '{%' in v):
            tpl += 1
            try:
                out = env.from_string(v).render()
                if 'undefined' in out.lower():
                    bad.append((path + '.' + k, 'undefined 输出', v[:70]))
            except Exception as e:
                bad.append((path + '.' + k, f'{type(e).__name__}: {e}', v[:90]))
        elif isinstance(v, (dict, list)):
            walk(v, path + '.' + k)

for v in cfg['views']:
    walk(v.get('cards'), v['path'])

print(f'模板 {tpl} 处，渲染失败 {len(bad)}')
for p, err, s in bad:
    print(f'  ✗ {p}\n     {err}\n     {s}')

if missing:
    print('\n缺失实体:')
    for m in missing:
        print('  ✗', m)

print('\n' + ('✓ 全部通过' if not bad and not missing else '✗ 需要修复'))
