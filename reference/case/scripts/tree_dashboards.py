"""把 lovelace 配置拍平成树状清单（只读，便于人工审阅）。
用法：python case/scripts/tree_dashboards.py [name]
"""
import json
import io
import sys

STATES = {e['entity_id']: e for e in json.load(io.open('.workbuddy/ha_states.json', encoding='utf-8'))}
NAME = sys.argv[1] if len(sys.argv) > 1 else 'overview_default'
cfg = json.load(io.open(f'.workbuddy/dashboards/{NAME}.json', encoding='utf-8'))


def fmt_state(eid):
    e = STATES.get(eid)
    if not e:
        return '∅'
    return e['state']


def walk(node, depth=0, idx=''):
    pad = '  ' * depth
    if isinstance(node, list):
        for i, x in enumerate(node):
            walk(x, depth, f'{idx}{i}')
        return
    if not isinstance(node, dict):
        return
    t = node.get('type', '?')
    label = node.get('title') or node.get('name') or node.get('heading') or ''
    eids = []
    for k in ('entity', 'entities'):
        if k in node:
            v = node[k]
            if isinstance(v, str):
                eids.append(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        eids.append(x)
                    elif isinstance(x, dict) and 'entity' in x:
                        eids.append(x['entity'])
    line = f"{pad}[{idx}] {t}"
    if label:
        line += f"  «{str(label)[:40]}»"
    if eids:
        line += '  → ' + ', '.join(f'{e}({fmt_state(e)})' for e in eids[:8])
    print(line)

    for key in ('cards', 'badges', 'sections'):
        if key in node:
            walk(node[key], depth + 1, idx + '.')
    for key in ('content', 'card', 'heading_card'):
        if key in node:
            walk(node[key], depth + 1, idx + '.')
    if 'columns' in node:  # grid
        walk(node['columns'], depth + 1, idx + '.')


walk({'cards': cfg.get('views', [{}])[0].get('cards', [])})
