"""只读：dump 区域 / 设备 / 实体注册表 + 实体状态汇总，用于规划新面板。
用法：python case/scripts/dump_registry.py
输出：.workbuddy/registry_summary.json + 控制台统计
"""
import json
import io
import collections
import websocket

HOST = '192.168.1.125:8123'
TOKEN = io.open('.workbuddy/ha_token.txt', encoding='utf-8').read().strip()
WS = f'ws://{HOST}/api/websocket'
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


ws = websocket.create_connection(WS, timeout=60)
json.loads(ws.recv())
ws.send(json.dumps({'type': 'auth', 'access_token': TOKEN}))
if json.loads(ws.recv()).get('type') != 'auth_ok':
    raise SystemExit('鉴权失败')

areas = call(ws, type='config/area_registry/list')
devices = call(ws, type='config/device_registry/list')
entities = call(ws, type='config/entity_registry/list')
floors = call(ws, type='config/floor_registry/list') if True else []
ws.close()

states = {e['entity_id']: e for e in json.load(io.open('.workbuddy/ha_states.json', encoding='utf-8'))}
dev_area = {d['id']: d.get('area_id') for d in devices}
dev_name = {d['id']: (d.get('name_by_user') or d.get('name') or '') for d in devices}
ent_area = {}
for e in entities:
    a = e.get('area_id') or dev_area.get(e.get('device_id'))
    ent_area[e['entity_id']] = a

json.dump({'areas': areas, 'floors': floors, 'devices': devices,
           'entities': entities, 'ent_area': ent_area},
          io.open('.workbuddy/registry_summary.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print(f'楼层 {len(floors)} / 区域 {len(areas)} / 设备 {len(devices)} / 实体注册 {len(entities)}')
print('\n=== 区域（含实体数 / 可控实体数）===')
cnt = collections.Counter(ent_area.values())
ctrl = collections.Counter()
for e in entities:
    if e['entity_id'].split('.')[0] in ('light', 'switch', 'fan', 'cover', 'climate', 'media_player',
                                        'vacuum', 'humidifier', 'water_heater', 'number', 'select', 'button'):
        ctrl[ent_area.get(e['entity_id'])] += 1
for a in sorted(areas, key=lambda x: x.get('name', '')):
    aid = a['id']
    print(f"  {aid:20} {a.get('name','')[:16]:18} 实体 {cnt[aid]:4}  可控 {ctrl[aid]:3}")

print('\n=== 未分配区域的实体（按 domain）===')
noarea = [e['entity_id'] for e in entities if not ent_area.get(e['entity_id'])]
print('  合计', len(noarea))
by_dom = collections.Counter(x.split('.')[0] for x in noarea)
print('  ', dict(by_dom.most_common(20)))
