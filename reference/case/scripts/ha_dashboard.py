"""通过 HA WebSocket API 创建/更新 Lovelace 面板（零重启）。

用法：
  python case/scripts/ha_dashboard.py list
  python case/scripts/ha_dashboard.py save "../HA Lovelace/lovelace/lovelace_monitor_dashboard.yaml" monitor-dashboard 屏幕 mdi:monitor-dashboard
"""
import json
import sys
import io

import websocket
import yaml

HOST = '192.168.1.125:8123'
TOKEN = io.open('.workbuddy/ha_token.txt', encoding='utf-8').read().strip()
WS = f'ws://{HOST}/api/websocket'

_id = [0]


def conn():
    ws = websocket.create_connection(WS, timeout=20)
    json.loads(ws.recv())                      # auth_required
    ws.send(json.dumps({'type': 'auth', 'access_token': TOKEN}))
    r = json.loads(ws.recv())
    if r.get('type') != 'auth_ok':
        raise SystemExit(f'鉴权失败: {r}')
    return ws


def call(ws, **payload):
    _id[0] += 1
    payload['id'] = _id[0]
    ws.send(json.dumps(payload, ensure_ascii=False))
    while True:
        r = json.loads(ws.recv())
        if r.get('id') == _id[0]:
            if not r.get('success'):
                raise SystemExit(f"失败 {payload['type']}: {r.get('error')}")
            return r.get('result')


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    ws = conn()
    try:
        if cmd == 'list':
            for d in call(ws, type='lovelace/dashboards/list'):
                print(f"{d.get('url_path'):24} {d.get('title')}  mode={d.get('mode')} "
                      f"sidebar={d.get('show_in_sidebar')}")
            return

        f = sys.argv[2]
        url_path = sys.argv[3] if len(sys.argv) > 3 else 'hmd'
        title = sys.argv[4] if len(sys.argv) > 4 else '屏幕镜像'
        # 侧边栏图标（用户 11-05：屏幕/掌控/中控 三个面板不能再共用一个图标）
        icon = sys.argv[5] if len(sys.argv) > 5 else 'mdi:monitor-dashboard'
        cfg = yaml.safe_load(io.open(f, encoding='utf-8').read())
        if 'views' not in cfg:
            raise SystemExit('配置里没有 views')

        existing = {d.get('url_path') for d in call(ws, type='lovelace/dashboards/list')}
        if url_path not in existing:
            call(ws,
                 type='lovelace/dashboards/create',
                 title=title,
                 url_path=url_path,
                 icon=icon,
                 show_in_sidebar=True,
                 require_admin=False,
                 mode='storage')
            print(f'✓ 已创建面板 {url_path}（{icon}）')
        else:
            print(f'· 面板 {url_path} 已存在，直接覆盖配置')

        call(ws, type='lovelace/config/save', url_path=url_path, config=cfg)
        print(f'✓ 配置已写入（{len(cfg["views"])} 个视图）：'
              + ', '.join(v.get('title', '?') for v in cfg['views']))
    finally:
        ws.close()


if __name__ == '__main__':
    main()
