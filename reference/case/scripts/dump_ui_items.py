# 临时：抽取四页 UI 的标签项（id + 文本/图标），用于 HA 页面复刻
import io
import re
import sys

FILES = ['ui/page_dashboard.yaml', 'ui/page_network.yaml',
         'ui/page_system.yaml', 'ui/page_notify.yaml']

for fn in FILES:
    print('\n========== %s ==========' % fn)
    lines = io.open(fn, encoding='utf-8').read().split('\n')
    cur_id = None
    for ln in lines:
        m = re.match(r'\s*id:\s*(\w+)\s*$', ln)
        if m:
            cur_id = m.group(1)
            continue
        m = re.match(r'\s*text:\s*(.+?)\s*$', ln)
        if m and cur_id:
            t = m.group(1)
            if t.startswith('"') and t.endswith('"'):
                v = t[1:-1]
                v = re.sub(r'\\U000F[0-9A-Fa-f]{4}', '[MDI]', v)
            else:
                v = '[lambda]'
            print('%-26s %s' % (cur_id, v[:50]))
            cur_id = None
