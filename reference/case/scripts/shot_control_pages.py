# -*- coding: utf-8 -*-
"""把「掌控」四个视图逐页截图为 PNG 并报告页长（给页长对齐用）。

用法：python case/scripts/shot_control_pages.py [视图序号...]
      python case/scripts/shot_control_pages.py          # 全部 4 页
产物：.workbuddy/cp{n}.png（880 宽 = 392 逻辑宽 × dpr2）
"""
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
NAMES = ['此刻', '能源', '房间', '安防']
BODY = (11, 11, 13)


def bottom(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    x = w // 2
    for y in range(h - 1, 0, -1):
        if px[x, y] != BODY and sum(px[x, y]) > 40:
            return y
    return 0


def main():
    idx = [int(a) for a in sys.argv[1:]] or list(range(1, len(NAMES) + 1))
    out = []
    for i in idx:
        html = os.path.join(ROOT, '.workbuddy', 'cp%d.html' % i)
        png = os.path.join(ROOT, '.workbuddy', 'cp%d.png' % i)
        subprocess.run([sys.executable, os.path.join(ROOT, 'case', 'scripts',
                                                     'preview_control_panel.py'),
                        '../HA Lovelace/lovelace/lovelace_phone_dashboard.yaml',
                        '.workbuddy/cp%d.html' % i, str(i)],
                       cwd=ROOT, check=True, capture_output=True)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=2', '--window-size=440,4000',
                        '--screenshot=' + png, 'file:///' + html.replace('\\', '/')],
                       check=True, capture_output=True)
        h = bottom(png) / 2
        out.append((NAMES[i - 1], h))
        print('%-4s 页长 %4d 逻辑px' % (NAMES[i - 1], h))
    base = dict(out).get('能源')
    if base and len(out) > 1:
        print('--- 以能源 %d 为基准 ---' % base)
        for nm, h in out:
            print('  %-4s %+5d  (%+.0f%%)' % (nm, h - base, (h - base) / base * 100))


if __name__ == '__main__':
    main()
