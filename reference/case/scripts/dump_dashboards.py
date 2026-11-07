"""只读：dump HA 所有 Lovelace 面板的完整配置到 .workbuddy/dashboards/
用法：cd "D:/HA Monitor Display" && python case/scripts/dump_dashboards.py
不写入 HA，只读取。
"""
import json
import os
import io
import websocket

HOST = '192.168.1.125:8123'
TOKEN = io.open('.workbuddy/ha_token.txt', encoding='utf-8').read().strip()
WS = f'ws://{HOST}/api/websocket'
OUT = '.workbuddy/dashboards'
_id = [0]


def call(ws, **payload):
    _id[0] += 1
    payload['id'] = _id[0]
    ws.send(json.dumps(payload, ensure_ascii=False))
    while True:
        r = json.loads(ws.recv())
        if r.get('id') == _id[0]:
            if not r.get('success'):
                return {'__error__': r.get('error')}
            return r.get('result')


def main():
    os.makedirs(OUT, exist_ok=True)
    ws = websocket.create_connection(WS, timeout=30)
    json.loads(ws.recv())
    ws.send(json.dumps({'type': 'auth', 'access_token': TOKEN}))
    r = json.loads(ws.recv())
    if r.get('type') != 'auth_ok':
        raise SystemExit(f'鉴权失败: {r}')

    dash = call(ws, type='lovelace/dashboards/list')
    print('=== 面板列表 ===')
    for d in dash:
        print(f"  {d.get('url_path'):24} {d.get('title')}  mode={d.get('mode')}")

    targets = [('overview_default', None)]
    for d in dash:
        targets.append((d.get('url_path'), d.get('url_path')))

    for name, url_path in targets:
        cfg = call(ws, type='lovelace/config', **({'url_path': url_path} if url_path else {}))
        if isinstance(cfg, dict) and '__error__' in cfg:
            print(f'  ! {name}: {cfg["__error__"]}')
            continue
        with io.open(f'{OUT}/{name}.json', 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        views = cfg.get('views', []) if isinstance(cfg, dict) else []
        cards = sum(len(v.get('cards', [])) for v in views)
        print(f'  ✓ {name}: {len(views)} 视图 / {cards} 顶层卡片 → {OUT}/{name}.json')
    ws.close()


if __name__ == '__main__':
    main()
