"""完整展开 lovelace 配置：栏目 → 卡片 → tab 标签 → 实体/模板摘要（只读）。
用法：python case/scripts/inspect_dash.py [name]
"""
import json
import io
import re
import sys

STATES = {e['entity_id']: e for e in json.load(io.open('.workbuddy/ha_states.json', encoding='utf-8'))}
NAME = sys.argv[1] if len(sys.argv) > 1 else 'overview_default'
cfg = json.load(io.open(f'.workbuddy/dashboards/{NAME}.json', encoding='utf-8'))

EID = re.compile(r'\b((?:sensor|binary_sensor|switch|light|fan|climate|input_[a-z]+|number|select|'
                 r'weather|person|device_tracker|cover|media_player|camera|zone|script|scene)\.[a-z0-9_]+)')


def st(e):
    e2 = STATES.get(e)
    if not e2:
        return '∅'
    s = e2['state']
    return s if len(s) < 18 else s[:17] + '…'


def ents_in(obj, out):
    if isinstance(obj, str):
        for m in EID.findall(obj):
            out.append(m)
    elif isinstance(obj, dict):
        for v in obj.values():
            ents_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            ents_in(v, out)


def brief(obj, width=70):
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    s = s.replace('\n', ' ⏎ ')
    return s if len(s) <= width else s[:width] + '…'


def walk(n, d=0):
    p = '  ' * d
    if isinstance(n, list):
        for x in n:
            walk(x, d)
        return
    if not isinstance(n, dict):
        return
    t = n.get('type', '?')
    head = f'{p}▸ {t}'
    if n.get('title'):
        head += f"  «{n['title']}»"
    if n.get('name') and t.endswith('person-card'):
        head += f"  «{n['name']}»"
    for k in ('entity',):
        if isinstance(n.get(k), str):
            head += f"  {n[k]}({st(n[k])})"
    if t == 'custom:mushroom-template-card':
        if n.get('primary'):
            head += f"  primary=«{brief(n['primary'], 46)}»"
        if n.get('secondary'):
            head += f"  sec=«{brief(n['secondary'], 46)}»"
    print(head)

    if t == 'custom:html-template-card':
        c = n.get('content', '')
        c = re.sub(r'<[^>]+>', ' ', c)
        print(f'{p}    content: {brief(c, 200)}')
        return
    if t == 'custom:tabbed-card':
        for tab in n.get('tabs', []):
            lbl = tab.get('attributes', {}).get('label', '?')
            print(f'{p}  ┌ TAB «{lbl}»')
            walk(tab.get('card'), d + 2)
        return
    if t == 'map':
        print(f'{p}    entities: {[e.get("entity") if isinstance(e, dict) else e for e in n.get("entities", [])]}')
        return
    if t == 'custom:webrtc-camera':
        print(f'{p}    url={n.get("url")} entity={n.get("entity")}')
        return

    for k in ('cards', 'badges', 'entities'):
        if k in n:
            walk(n[k], d + 1)
    if isinstance(n.get('card'), (dict, list)):
        walk(n['card'], d + 1)
    if isinstance(n.get('content'), (dict, list)):
        walk(n['content'], d + 1)


views = cfg.get('views', [])
for vi, v in enumerate(views):
    print(f'###### VIEW {vi}  path={v.get("path")} type={v.get("type")}')
    for ci, card in enumerate(v.get('cards', [])):
        print(f'--- 第 {ci + 1} 栏 ---')
        walk(card, 0)
    print()
