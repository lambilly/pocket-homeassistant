"""把渲染好的镜像页 HTML 按四页切开，逐页截图为 PNG，存进 hardware/。

用法：
    python case/scripts/shot_mirror_pages.py

前置：.workbuddy/mirror_render.html 已由 HA 模板接口渲染（见项目对话记录里的渲染片段）。
产物：hardware/屏幕镜像1-家居.png … 屏幕镜像4-通知.png（430 逻辑宽 × dpr2 = 860px）
"""
import io
import os
import re
import subprocess
import sys

from fontTools.ttLib import TTFont
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, '.workbuddy', 'mirror_render.html')
FONT = os.path.join(ROOT, 'fonts', 'materialdesignicons-webfont.ttf')
OUTDIR = os.path.join(ROOT, 'hardware')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
NAMES = ['家居', '网络', '系统', '通知']

TAB_RE = re.compile(r'<div class="tab">[\s\S]*?</div>\s*</div>')
ICON_RE = re.compile(r'<ha-icon[^>]*>(?:</ha-icon>)?')
STYLE_RE = re.compile(r'<style>[\s\S]*?</style>')

EXTRA_CSS = """
<style>
@font-face{font-family:mdif;src:url("file:///%(font)s")}
.mdi{font-family:mdif;font-style:normal;line-height:1;display:inline-block;font-size:10px !important}
.hd .mdi{font-size:12px !important}
.hc .mdi{font-size:14px !important}
.c5 .mdi{font-size:9px !important}
.c9 .mdi{font-size:10px !important}
*{box-sizing:border-box}
body{margin:0;background:#000;display:flex;justify-content:center;padding:0}
.ph{width:430px;background:#0F0F0F}
.ph .hmd{width:430px !important;margin:0 !important}
</style>
"""


def split_pages(html):
    tabs = list(TAB_RE.finditer(html))
    if len(tabs) != 4:
        sys.exit('TAB 块数量不是 4，实际 %d' % len(tabs))
    start = html.find('<div class="hmd">') + len('<div class="hmd">')
    if start < len('<div class="hmd">'):
        sys.exit('找不到 <div class="hmd">')
    return [
        html[start:tabs[0].end()],
        html[tabs[0].end():tabs[1].end()],
        html[tabs[1].end():tabs[2].end()],
        html[tabs[2].end():html.rfind('</div>')],
    ]


def make_converter():
    rev = {nm: cp for cp, nm in TTFont(FONT).getBestCmap().items()}

    def conv(m):
        tag = m.group(0)
        ic = re.search(r'icon="mdi:([^"]+)"', tag)
        cp = rev.get(ic.group(1)) if ic else None
        col = re.search(r'color:(#[0-9A-Fa-f]{6})', tag)
        va = 'vertical-align:-2px;' if 'vertical-align:-2px' in tag else ''
        if not cp:
            return '<i style="display:inline-block;width:10px"></i>'
        return '<i class="mdi" style="color:%s;%s">%s</i>' % (
            col.group(1) if col else '#FFF', va, chr(cp))
    return conv


def trim_to_content(path):
    """按内容白边框自动裁掉四周空白（Chrome 视口居中偏移不固定，不能写死 x）。"""
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    xs, last = [], 0
    for y in range(h - 1, 0, -1):
        row = [x for x in range(w) if px[x, y][0] > 200 and px[x, y][1] > 200 and px[x, y][2] > 200]
        if row:
            last = y
            break
    for y in range(0, last + 1, 2):
        row = [x for x in range(w) if px[x, y][0] > 200 and px[x, y][1] > 200 and px[x, y][2] > 200]
        if row:
            xs += [min(row), max(row)]
    x0, x1 = max(min(xs) - 8, 0), min(max(xs) + 8, w)
    return im.crop((x0, 0, x1, last + 14))


def main():
    html = io.open(SRC, encoding='utf-8').read()
    style = STYLE_RE.search(html).group(0)
    conv = make_converter()
    pages = split_pages(html)
    print('四页片段长度:', [len(p) for p in pages])

    for i, pg in enumerate(pages, 1):
        body = ICON_RE.sub(conv, pg)
        out_html = os.path.join(ROOT, '.workbuddy', 'mirror_page%d.html' % i)
        io.open(out_html, 'w', encoding='utf-8').write(
            '<!DOCTYPE html><html><head><meta charset="utf-8">\n%s\n%s</head>'
            '<body><div class="ph"><div class="hmd">%s</div></div></body></html>'
            % (style, EXTRA_CSS % {'font': FONT.replace('\\', '/')}, body))
        shot = os.path.join(ROOT, '.workbuddy', 'mp%d.png' % i)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=2', '--window-size=470,1800',
                        '--screenshot=' + shot, 'file:///' + out_html.replace('\\', '/')],
                       check=True, capture_output=True)
        img = trim_to_content(shot)
        dst = os.path.join(OUTDIR, '屏幕镜像%d-%s.png' % (i, NAMES[i - 1]))
        img.save(dst)
        print('%s %s' % (os.path.basename(dst), img.size))


if __name__ == '__main__':
    main()
