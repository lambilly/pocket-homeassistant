"""校验 Lovelace 镜像页引用的实体是否真实存在、状态是否可用。
用法：cd "D:/HA Monitor Display" && python case/scripts/check_entities.py
读 .workbuddy/ha_states.json（curl /api/states 的原始结果）
"""
import json, io, re, sys

YAML = 'HA Lovelace/lovelace/lovelace_monitor_dashboard.yaml'
STATES = '.workbuddy/ha_states.json'

states = {e['entity_id']: e for e in json.load(io.open(STATES, encoding='utf-8'))}
src = io.open(YAML, encoding='utf-8').read()

# 收集所有 entity_id 形态的引用
refs = set(re.findall(r'\b([a-z_]+\.[a-z0-9_]+)\b', src))
refs = {r for r in refs if r.split('.')[0] in (
    'sensor', 'binary_sensor', 'switch', 'light', 'fan', 'climate',
    'input_text', 'input_boolean', 'input_number', 'number', 'select',
    'weather', 'device_tracker', 'person', 'cover', 'media_player')}

print(f'引用实体 {len(refs)} 个')
bad, warn, good = [], [], []
for r in sorted(refs):
    e = states.get(r)
    if e is None:
        bad.append(r)
        continue
    st = e['state']
    if st in ('unavailable', 'unknown'):
        warn.append((r, st))
    else:
        good.append((r, st))

print(f'\n=== 缺失 {len(bad)} ===')
for r in bad:
    print('  ✗', r)
print(f'\n=== 状态异常 {len(warn)} ===')
for r, st in warn:
    print('  !', r, '=', st)
print(f'\n=== 正常 {len(good)} ===')
for r, st in good:
    print('  ✓', f'{r:56}', st[:40])
