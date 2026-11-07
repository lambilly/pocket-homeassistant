# -*- coding: utf-8 -*-
"""在 HA 里创建/检查中控配色用的 input_select（走 WebSocket storage 集合，零重启）。

用法：
  python hmd_helper.py probe     # 看现有 input_select 与命令可用性
  python hmd_helper.py ensure    # 不存在就创建并规范 entity_id 为 input_select.hmd_theme
"""
import io
import json
import sys

import websocket

HOST = '192.168.1.125:8123'
TOKEN = io.open(r'D:\HA Monitor Display\.workbuddy\ha_token.txt',
                encoding='utf-8').read().strip()
WS_URL = 'ws://' + HOST + '/api/websocket'

OPTIONS = ['紫', '蓝', '青', '绿', '琥珀', '红', '石墨']
NAME = '中控配色'
# 关键：先用英文建，entity_id 才能精确等于 hmd_theme（中文名会把 slug 变成拼音）
CREATE_NAME = 'HMD Theme'
TARGET_EID = 'input_select.hmd_theme'

_id = [0]


def conn():
    ws = websocket.create_connection(WS_URL, timeout=20)
    json.loads(ws.recv())
    ws.send(json.dumps({'type': 'auth', 'access_token': TOKEN}))
    r = json.loads(ws.recv())
    if r.get('type') != 'auth_ok':
        raise SystemExit('鉴权失败: ' + str(r))
    return ws


def call(ws, allow_fail=False, **payload):
    _id[0] += 1
    payload['id'] = _id[0]
    ws.send(json.dumps(payload, ensure_ascii=False))
    while True:
        r = json.loads(ws.recv())
        if r.get('id') == _id[0]:
            if not r.get('success'):
                if allow_fail:
                    return {'_error': r.get('error')}
                raise SystemExit('失败 ' + payload['type'] + ': ' + str(r.get('error')))
            return r.get('result')


def states(ws):
    return call(ws, type='get_states')


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'probe'
    ws = conn()
    try:
        cur = [s for s in states(ws) if s['entity_id'].startswith('input_select.')]
        print('现有 input_select %d 个：' % len(cur))
        for s in cur:
            print('   ', s['entity_id'], '=', s['state'])

        hit = [s for s in cur if s['entity_id'] == TARGET_EID]
        if hit:
            print('\n✓ 已存在', TARGET_EID, '当前值', hit[0]['state'])
            if cmd == 'ensure':
                call(ws, type='input_select/update',
                     input_select_id=None) if False else None
            return

        if cmd == 'probe':
            r = call(ws, allow_fail=True, type='input_select/list')
            print('\ninput_select/list ->', 'OK' if '_error' not in r else r['_error'])
            return

        # ---- 创建 ----
        r = call(ws, allow_fail=True, type='input_select/create',
                 name=CREATE_NAME, options=OPTIONS, initial=OPTIONS[0],
                 icon='mdi:palette')
        if '_error' in r:
            print('✗ input_select/create 失败:', r['_error'])
            return
        print('✓ 已创建，返回:', json.dumps(r, ensure_ascii=False)[:300])

        # ---- 找到新实体并规范 entity_id / 显示名 ----
        reg = call(ws, type='config/entity_registry/list')
        cand = [e for e in reg
                if e.get('platform') == 'input_select'
                and e.get('original_name') in (CREATE_NAME, NAME)]
        if not cand:
            cand = [e for e in reg if e.get('platform') == 'input_select']
        if not cand:
            print('! 实体注册表里没找到，稍后手动确认')
            return
        ent = cand[-1]
        print('  新建实体：', ent['entity_id'])
        upd = {}
        if ent['entity_id'] != TARGET_EID:
            upd['new_entity_id'] = TARGET_EID
        if not ent.get('name'):
            upd['name'] = NAME          # 只改显示名，不动 entity_id
        if upd:
            r2 = call(ws, allow_fail=True, type='config/entity_registry/update',
                      entity_id=ent['entity_id'], **upd)
            print('  更新 <' + ', '.join(upd) + '>:',
                  'OK' if '_error' not in r2 else r2['_error'])
        print('✓ 完成')
    finally:
        ws.close()


if __name__ == '__main__':
    main()
