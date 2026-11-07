# -*- coding: utf-8 -*-
"""外壳 v2 剖面图：天线槽 / 窗口沿口 / 螺丝头座
输出 02_v2_fixes/preview_slot.png、preview_rim.png、preview_screw.png
运行：cd case && python scripts/preview_v5.py
"""
import os
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from trimesh.intersections import mesh_plane

np.seterr(all='ignore')
CASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(CASE)
OUT = '02_v2_fixes'
TOTAL = 16.8 + 16.2
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

C_REAR, C_FRONT = '#e07a5f', '#3d7ea6'
C_DIM = '#555'


def load_as(rear, front):
    r = trimesh.load(rear, force='mesh')
    f = trimesh.load(front, force='mesh')
    f.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    f.apply_translation([0, 0, TOTAL])
    return r, f


def seg(mesh, origin, normal):
    s = mesh_plane(mesh, normal, origin)
    return np.zeros((0, 2, 3)) if s is None or len(s) == 0 else s


def draw(ax, meshes, origin, normal, zoom, title, ij=(0, 2), hline=None):
    for m, c, lab in meshes:
        s = seg(m, origin, normal)
        for k, sgm in enumerate(s):
            ax.plot(sgm[:, ij[0]], sgm[:, ij[1]], color=c, lw=1.2,
                    label=lab if k == 0 else None)
    ax.set_aspect('equal')
    ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
    ax.set_title(title, fontsize=9.5)
    ax.grid(alpha=0.25, lw=0.5)
    if hline is not None:
        ax.axhline(hline[0], color='#888', ls='--', lw=0.8)
        ax.text(zoom[0] + 0.2, hline[0] + 0.08, hline[1], fontsize=6.8, color='#888')


def dim(ax, x0, x1, y, text, color='#c0392b'):
    ax.annotate('', xy=(x0, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='<->', color=color, lw=1.0))
    ax.text((x0 + x1)/2, y, text, ha='center', va='bottom',
            fontsize=8, color=color)


v3r, v3f = load_as('02_v1_fixes/rear_v1.stl', '02_v1_fixes/front_v1.stl')
v5r, v5f = load_as(f'{OUT}/rear_v2.stl', f'{OUT}/front_v2.stl')

# ========== ④ 天线让位槽（-Y 短边框内壁横向盲槽）==========
SLOT_XC, SLOT_ZC = 9.55, 7.0
SLOT_L, SLOT_H = 20.0, 3.0
fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6))
# (a) 过槽中心的竖剖（(y,z) 面，法向 X）→ 看挖深、剩皮、槽宽
draw(axes[0], [(v5r, C_REAR, '后盖 v2')], [SLOT_XC, 0, 0], [1, 0, 0],
     (-52.9, -47.9, 4.4, 9.9),
     'A–A：过槽中心竖剖（x = +9.55）\n端壁 2.0 挖深 1.2 → 外壁留 0.8 皮（不透）', ij=(1, 2))
ax = axes[0]
for yv in (-51.3, -50.5, -49.3):
    ax.axvline(yv, color='#2c7a4b', lw=0.9, ls='--')
for zv in (SLOT_ZC - SLOT_H/2, SLOT_ZC + SLOT_H/2):
    ax.axhline(zv, color='#2c7a4b', lw=0.9, ls='--')
dim(ax, -50.5, -49.3, 9.1, '挖深 1.2')
dim(ax, -51.3, -50.5, 4.9, '剩皮 0.8', color='#2c7a4b')
ax.annotate('', xy=(-52.35, SLOT_ZC - SLOT_H/2), xytext=(-52.35, SLOT_ZC + SLOT_H/2),
            arrowprops=dict(arrowstyle='<->', color='#2c7a4b', lw=1.0))
ax.text(-52.55, SLOT_ZC, '槽宽\n3.0', fontsize=7.5, color='#2c7a4b',
        rotation=90, va='center', ha='right')
ax.set_xlabel('y (mm)'); ax.set_ylabel('z (mm)')
ax.legend(fontsize=7, loc='upper right')
# (b) 槽底内横剖（(x,z) 面，法向 Y）→ 看槽长、距边
draw(axes[1], [(v5r, C_REAR, '后盖 v2')], [0, -50.4, 0], [0, 1, 0],
     (-32.0, 32.0, -0.9, 17.9),
     'B–B：槽底内正视剖（y = −50.4）\n槽 20 × 3，起点距 +X 长边 10.5', ij=(0, 2))
ax = axes[1]
for xv in (SLOT_XC - SLOT_L/2, SLOT_XC + SLOT_L/2):
    ax.axvline(xv, color='#2c7a4b', lw=0.9, ls='--')
for zv in (SLOT_ZC - SLOT_H/2, SLOT_ZC + SLOT_H/2):
    ax.axhline(zv, color='#2c7a4b', lw=0.9, ls='--')
dim(ax, SLOT_XC - SLOT_L/2, SLOT_XC + SLOT_L/2, 15.6, '槽长 20')
dim(ax, SLOT_XC + SLOT_L/2, 30.05, 15.6, '10.5', color='#2c7a4b')
ax.annotate('', xy=(-30.05, 4.8), xytext=(30.05, 4.8),
            arrowprops=dict(arrowstyle='<->', color='#888', lw=1.0))
ax.text(0, 3.8, '后盖宽 60.1', ha='center', fontsize=7.2, color='#888')
ax.text(SLOT_XC, SLOT_ZC, '槽区', ha='center', va='center', fontsize=7.5, color='#2c7a4b')
ax.set_xlabel('x (mm)'); ax.set_ylabel('z (mm)')
fig.suptitle('④ ESP32-S3 天线让位槽（−Y 短边框内壁横向盲槽，正对 +Y 端 Type-C 开口，不透）',
             fontsize=10.5)
fig.tight_layout()
fig.savefig(f'{OUT}/preview_slot.png', dpi=170)
print(f'→ {OUT}/preview_slot.png')

# ========== ② 窗口沿口 ==========
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
draw(axes[0], [(v3f, C_FRONT, '前壳 v1')], [0, 0, 0], [0, 1, 0],
     (23.5, 30.4, 30.6, 33.25),
     'v1 回货版：内壁 45° 羽状斜边\n沿口最薄 0.8，屏台阶 32.2')
axes[0].annotate('', xy=(25.28, 33.0), xytext=(25.28, 32.2),
                 arrowprops=dict(arrowstyle='<->', color='#c0392b', lw=1.0))
axes[0].text(25.45, 32.5, '0.8', fontsize=8, color='#c0392b')
draw(axes[1], [(v5f, C_FRONT, '前壳 v2')], [0, 0, 0], [0, 1, 0],
     (23.5, 30.4, 30.6, 33.25),
     'v2：31.8~32.6 直壁（49.76，内收 0.4 遮黑边）\n32.6~33.0 保留原 45° 内倾斜边；沿口总厚 1.20')
axes[1].annotate('', xy=(25.28, 33.0), xytext=(25.28, 31.8),
                 arrowprops=dict(arrowstyle='<->', color='#2c7a4b', lw=1.0))
axes[1].text(25.45, 32.2, '1.20', fontsize=8, color='#2c7a4b')
for ax in axes:
    ax.axvline(25.28, color=C_DIM, lw=0.7, ls=':')
    ax.axvline(28.05, color=C_DIM, lw=0.7, ls=':')
    ax.set_xlabel('x (mm)'); ax.set_ylabel('z (mm)')
    ax.legend(fontsize=7, loc='lower right')
fig.suptitle('② 屏幕窗口沿口剖面（y = 0 平面，+X 边局部放大；v2 悬挑 0.8 → 0.4）', fontsize=11)
fig.tight_layout()
fig.savefig(f'{OUT}/preview_rim.png', dpi=170)
print(f'→ {OUT}/preview_rim.png')

# ========== ⑤ 螺丝头座 ==========
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
draw(axes[0], [(v3r, C_REAR, '后盖'), (v3f, C_FRONT, '前壳')], [0, 46.0, 0], [0, 1, 0],
     (20.5, 29.5, 8.0, 33.0),
     'v4：头座 12.15 → 原 M2×9.5 只到 21.65\n咬合 0.2 → 不可用（故要换 M2×14）',
     ij=(0, 2), hline=(16.8, '接缝 16.8'))
draw(axes[1], [(v5r, C_REAR, '后盖 v2'), (v5f, C_FRONT, '前壳 v2')], [0, 46.0, 0], [0, 1, 0],
     (20.5, 29.5, 8.0, 33.0),
     'v2：头座加深到 15.6\n原 M2×9.5 咬合 3.65，不用换螺丝',
     ij=(0, 2), hline=(16.8, '接缝 16.8'))
for ax, seat, col in ((axes[0], 12.15, '#c0392b'), (axes[1], 15.6, '#2c7a4b')):
    ax.axhline(seat, color=col, lw=0.9, ls='--')
    ax.axhline(25.65 if seat < 13 else 25.45, color=col, lw=0.9, ls=':')
    ax.annotate('', xy=(25.9, seat), xytext=(25.9, seat + 9.5),
                arrowprops=dict(arrowstyle='-|>', color=col, lw=1.1))
    ax.text(26.0, (seat + seat + 9.5)/2, 'M2×9.5', fontsize=7, color=col, rotation=90,
            va='center')
    ax.set_xlabel('x (mm)'); ax.set_ylabel('z (mm)')
    ax.legend(fontsize=7, loc='upper left')
fig.suptitle('⑤ 螺丝通道剖面（y = 46 平面，+X 角柱；咬合面 z = 21.45）', fontsize=11)
fig.tight_layout()
fig.savefig(f'{OUT}/preview_screw.png', dpi=170)
print(f'→ {OUT}/preview_screw.png')
