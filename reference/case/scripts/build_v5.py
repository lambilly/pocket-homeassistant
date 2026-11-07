# -*- coding: utf-8 -*-
"""
HA Monitor Display 外壳 v5 生成器（2026-11-04 晚，回货第二批反馈）
在 v4（螺丝柱前删后加长 / Type-C 下移 7.0 / 孔距 15.78 / 喇叭口）基础上追加：

① 旧 Type-C 固定孔删除：真位置 x=±8.0（v4 误记 ±5.7，回填落空）→ 补填 ⌀2.54
② 屏幕窗口沿口加厚：原沿口 45° 内倾羽状斜边（高仅 0.8mm，悬挑打印缺口）
   → 31.8~32.6 改直壁（口径 49.76，内收 0.4），32.6~33.0 保留原 45° 内倾斜面 = 正面斜边
   → 沿口总厚 0.8 → 1.20mm（0.8 直壁 + 0.4 斜边）；悬挑减半；屏幕下沉 0.4mm
③ 透气孔：用户取消，不开
④ ESP32-S3 天线让位槽：开在 -Y 短边框（与 +Y 端 Type-C 开口正对）的**内壁面**上
   横向盲槽 20×3：长沿 X（x -0.45~19.55，起点距 +X 长边 10.5）、
   宽沿 Z（z 5.5~8.5，中心距后盖外表面 7.0）、挖深 1.2（壁 2.0 → 外壁留 0.8 皮，不透）
⑤ 螺丝孔加深：沿用原 M2×9.5（⌀1.9 圆头十字自攻），⌀5.0 头座由 12.15 加深到 15.6
   → 旋入后咬合前壳角台底孔 3.65mm（v4 的 12.15 只够 0.2mm，故原要求换 M2×14）

输出：02_v2_fixes/rear_v2.stl + front_v2.stl（打印批次编号：已打印回货= v1，本版 = v2）
      + 剖面对比图
运行：cd case && python scripts/build_v5.py
"""
import os
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely.affinity import translate as s_translate
from trimesh.creation import extrude_polygon, cylinder

np.seterr(all='ignore')
CASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(CASE)
SRC_REAR, SRC_FRONT = '02_v1_fixes/rear_v1.stl', '02_v1_fixes/front_v1.stl'
OUT = '02_v2_fixes'
os.makedirs(OUT, exist_ok=True)
ENG = 'manifold'
SEAM, TOTAL = 16.8, 33.0

# ---------- 后盖 +Y 端壁 ----------
WALL_IN, WALL_OUT = 49.3, 51.3
FLOOR_TOP = 3.5
ZC = FLOOR_TOP + 3.5                    # 7.0  Type-C 中心高
PITCH = 15.78 / 2                       # ±7.89
THROAT = (9.0, 3.4, 1.0)
FLARE = (11.0, 5.4, 1.5)
FLARE_Y0 = 50.7
HOLE_R = 1.1
CSK_R, CSK_DEPTH = 2.1, 1.2
OLD_OPEN = dict(zc=12.65, w=9.0, h=3.3, r=1.0)
OLD_HOLE = dict(x=8.0, zc=12.65, r=1.25)     # ← 实测真位置（v4 误记 5.7）

# ---------- 天线让位槽（④，-Y 短边框内壁横向盲槽，正对 +Y 端 Type-C 开口）----------
SLOT_L, SLOT_H = 20.0, 3.0              # 长（x）× 宽（z）
SLOT_R = 1.0
SLOT_XC = 9.55                          # x -0.45~19.55：起点距 +X 长边 10.5（原记 -X 侧，用户更正）
SLOT_ZC = 7.0                           # z 5.5~8.5：中心距后盖外表面（底）7.0
SLOT_Y0, SLOT_Y1 = -50.5, -48.9         # 挖深 1.2（内壁 -49.3），外壁留 0.8 皮 → 不透

# ---------- 螺丝柱（沿 v4）----------
POST = [(24.75, 46.0), (-24.75, 46.0), (24.75, -46.0), (-24.75, -46.0)]
COL_R = 3.0
EXT_Z0, EXT_TOP = 12.0, 21.40
BORE_R = 1.15
FACE_W = 21.45
PILOT_R = 0.85
PILOT_W0, PILOT_W1 = FACE_W, 28.5
PIN_CUT_R = 2.0

# ---------- 螺丝头座（⑤）world 坐标 ----------
WELL_W = 15.6                           # ⌀5.0 头座底（原 12.15）；原 M2×9.5 杆长
SCREW_L = 9.5                           # 咬合 = WELL_W + SCREW_L - FACE_W = 3.65

# ---------- 窗口沿口（②）world 坐标 ----------
WIN_W, WIN_Y0, WIN_Y1 = 50.56, -40.15, 34.89   # 正面开口实测（y 不居中）
POCK_HW, POCK_HH = 28.05, 42.78                # 坐屏口袋半宽
LIP_SEAT_W = 31.8                       # 新沿口下沿（原 32.2）→ 总厚 1.2
RING_TOP_W = 32.35                      # 补料环上端（插进现有料内，避免共面）
RIM_PAD = 0.35                          # 补料环外扩（探进口袋壁里）
CHAM = 0.4                              # 正面 45° 斜边高（32.6~33.0，用户要求恢复）


# ================= 工具 =================
def rrect(w, h, r, zc=0.0, xc=0.0):
    base = sbox(-(w/2 - r), -(h/2 - r), (w/2 - r), (h/2 - r)).buffer(r, resolution=32).buffer(0)
    base = s_translate(base, xc, 0)
    return s_translate(base, 0, zc) if zc else base


def rect_poly(w, y0, y1):
    """以 x 居中、y 取 [y0,y1] 的轴对齐矩形"""
    return sbox(-w/2, y0, w/2, y1)


def prism_xz(poly, y0, y1):
    """(x,z) 多边形沿 Y 拉伸"""
    ring = [(x, z) for x, z in zip(*poly.exterior.coords.xy)]
    holes = [[(x, z) for x, z in zip(*i.coords.xy)] for i in poly.interiors]
    m = extrude_polygon(Polygon(ring, holes), height=y1 - y0)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m


def prism_z(poly, z0, z1):
    """(x,y) 多边形沿 Z 拉伸"""
    m = extrude_polygon(orient(poly, 1.0), height=z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def cyl_y(x, zc, r, y0, y1, sec=64):
    c = cylinder(radius=r, height=y1 - y0, sections=sec)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1)/2, zc])
    return c


def cyl_z(x, y, z0, z1, r, sec=64):
    c = cylinder(radius=r, height=z1 - z0, sections=sec)
    c.apply_translation([x, y, (z0 + z1)/2])
    return c


def taper_y(x, zc, y_wide, y_narrow, r_wide, r_narrow, steps=4):
    ms = []
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        ya = y_wide + (y_narrow - y_wide) * t0
        yb = y_wide + (y_narrow - y_wide) * t1
        rr = r_wide + (r_narrow - r_wide) * ((t0 + t1) / 2)
        ms.append(cyl_y(x, zc, rr, min(ya, yb), max(ya, yb)))
    return trimesh.boolean.union(ms, engine=ENG)


def loft(poly0, z0, poly1, z1, n=256):
    """两平行平面间的直纹放样（顶点重采样对齐）"""
    from shapely.geometry import LinearRing

    def sample(poly):
        ring = LinearRing(orient(poly, 1.0).exterior.coords)
        L = ring.length
        return np.array([[ (p := ring.interpolate(L*i/n)).x, p.y] for i in range(n)])

    P0, P1 = sample(poly0), sample(poly1)
    V = np.vstack([
        np.column_stack([P0, np.full(n, z0)]),
        np.column_stack([P1, np.full(n, z1)]),
        [[0, 0, z0], [0, 0, z1]]])
    F, c0, c1 = [], 2*n, 2*n + 1
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i]]
        F += [[c0, j, i], [c1, n + i, n + j]]
    m = trimesh.Trimesh(vertices=V, faces=np.array(F), process=True)
    assert m.is_watertight, 'loft 不密闭'
    if m.volume < 0:
        m.invert()
    return m


def dif(a, b):
    return trimesh.boolean.difference([a, b], engine=ENG)


def uni(*ms):
    return trimesh.boolean.union(list(ms), engine=ENG)


res = []


def ok(name, cond, extra=''):
    print(f'  [{"PASS" if cond else "FAIL"}] {name} {extra}')
    res.append(bool(cond))


def window_poly(f_world, z):
    """从 world 前壳切片取窗口内环 → shapely Polygon"""
    sec = f_world.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    best = None
    for ent in sec.entities:
        pts = sec.vertices[ent.points][:, :2]
        if np.abs(pts[:, 0]).max() < 29:                # 排除外轮廓（只按 x）
            if best is None or len(pts) > len(best):
                best = pts
    assert best is not None
    if np.allclose(best[0], best[-1]):
        best = best[:-1]
    return Polygon(best).buffer(0)


# ================= 后盖 =================
print('=' * 70)
print('rear_v3 → rear_v2（打印批次 v2）')
r0 = trimesh.load(SRC_REAR, force='mesh')
assert r0.is_watertight
print(f'  源: 体积={r0.volume:.0f}mm³')

r = r0.copy()
# 1) 回填旧 Type-C 口 + 旧固定孔 ±8.0
fillers = [prism_xz(rrect(OLD_OPEN['w'] + 0.1, OLD_OPEN['h'] + 0.1, OLD_OPEN['r'], OLD_OPEN['zc']),
                    WALL_IN, WALL_OUT)]
for sx in (1, -1):
    fillers.append(cyl_y(sx * OLD_HOLE['x'], OLD_HOLE['zc'], OLD_HOLE['r'] + 0.02,
                         WALL_IN, WALL_OUT))
r = uni(r, *fillers)
print(f'  回填后: wt={r.is_watertight} 体积={r.volume:.0f}mm³')

# 2) 螺丝柱加长段
r = uni(r, *[cyl_z(x, y, EXT_Z0, EXT_TOP, COL_R) for (x, y) in POST])

# 3) 端壁开孔 + 通孔 + 沉头
cutters = [
    prism_xz(rrect(*THROAT, zc=ZC), WALL_IN - 0.3, WALL_OUT + 0.3),
    prism_xz(rrect(*FLARE, zc=ZC), FLARE_Y0, WALL_OUT + 0.3),
]
for sx in (1, -1):
    cutters.append(cyl_y(sx * PITCH, ZC, HOLE_R, WALL_IN - 0.3, WALL_OUT + 0.3))
    cutters.append(taper_y(sx * PITCH, ZC, WALL_OUT + 0.05, WALL_OUT - CSK_DEPTH,
                           CSK_R, HOLE_R, steps=4))
for (x, y) in POST:
    cutters.append(cyl_z(x, y, EXT_Z0, EXT_TOP + 0.2, BORE_R))
    cutters.append(cyl_z(x, y, -0.3, WELL_W, 2.5))      # ⑤ ⌀5.0 头座加深到 15.6

# 4) 天线让位槽（-Y 短边框内壁横向盲槽：沿 X 长 20、沿 Z 宽 3、挖深 1.2 留 0.8 皮）
cutters.append(prism_xz(rrect(SLOT_L, SLOT_H, SLOT_R, zc=SLOT_ZC, xc=SLOT_XC),
                        SLOT_Y0, SLOT_Y1))
r = dif(r, uni(*cutters))
print(f'  成型后: wt={r.is_watertight} 体积={r.volume:.0f}mm³ bounds={np.round(r.bounds,2).tolist()}')
p_rear = f'{OUT}/rear_v2.stl'
r.export(p_rear)
print(f'  → {p_rear}  faces={len(r.faces)}')

# ================= 前壳 =================
print('=' * 70)
print('front_v4（已打印版） → front_v2（细柱删除 + 窗口沿口加厚 + 正面斜边）')
f0 = trimesh.load(SRC_FRONT, force='mesh')
assert f0.is_watertight

# 先切细柱 + 钻底孔（v4 逻辑，stored 坐标）
cut_z0 = TOTAL - FACE_W
cut_z1 = TOTAL - 16.0
pil_z0, pil_z1 = TOTAL - PILOT_W1, TOTAL - PILOT_W0
cutters = []
for (x, y) in POST:
    cutters.append(cyl_z(x, y, cut_z0, cut_z1, PIN_CUT_R))
    cutters.append(cyl_z(x, y, pil_z0, pil_z1, PILOT_R))
f = dif(f0.copy(), uni(*cutters))

# 窗口沿口：world → stored（s = 33 - w）
fw = f.copy()
fw.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
fw.apply_translation([0, 0, TOTAL])
P_POCK = window_poly(fw, 31.0)           # 坐屏口袋轮廓（干净环，n≈265）
# 窗口开口实测是 world 值；前壳装配绕 X 翻 180°，故 stored 的 y 要取反
OPEN = rect_poly(WIN_W, -WIN_Y1, -WIN_Y0)
OPEN_IN = OPEN.buffer(-CHAM, resolution=16).buffer(0)  # 直壁口径 = 开口内收 0.4（斜边下端）
RING_OUT = P_POCK.buffer(RIM_PAD, resolution=16).buffer(0)
LIP_RING = Polygon(RING_OUT.exterior, [OPEN_IN.exterior])
print(f'  窗口: 开口 {WIN_W:.2f}×{WIN_Y1-WIN_Y0:.2f}'
      f'  口袋 x±{P_POCK.bounds[2]:.2f} y±{P_POCK.bounds[3]:.2f}'
      f'  沿口环面积 {LIP_RING.area:.0f}mm²')

# ② 沿口加厚（不取截面轮廓，只靠实测矩形 + 口袋环）
#   a) 补料：口袋轮廓范围内、开口外扩轮廓之外，从 32.35 补到 31.8（探进现有料 0.15）
f = uni(f, prism_z(LIP_RING, TOTAL - RING_TOP_W, TOTAL - LIP_SEAT_W))
#   b) 直壁：31.8~32.6 竖壁（口径 49.76，内收 0.4）；32.6~33.0 保留原 45° 内倾斜面
#      = 正面斜边（原斜面恰好过 (24.88, 32.6)，与直壁无缝衔接，无需另切锥面）
f = dif(f, prism_z(OPEN_IN, TOTAL - 32.62, TOTAL - LIP_SEAT_W))
print(f'  沿口加厚后: wt={f.is_watertight} 体积={f.volume:.0f}mm³ bounds={np.round(f.bounds,2).tolist()}')
p_front = f'{OUT}/front_v2.stl'
f.export(p_front)
print(f'  → {p_front}  faces={len(f.faces)}')

# ================= 校验 =================
print('=' * 70)
print('校验')
ok('后盖 watertight', r.is_watertight)
nb = len(r.split(only_watertight=False))
ok('后盖 单一实体', nb == 1, f'实体数={nb}')
ok('前壳 watertight', f.is_watertight)
nf = len(f.split(only_watertight=False))
ok('前壳 单一实体', nf == 1, f'实体数={nf}')
ok('后盖外形 60.1×102.6×21.40', np.allclose(r.extents, [60.1, 102.6, EXT_TOP], atol=0.06),
   np.round(r.extents, 2).tolist())
ok('前壳外形 60.1×102.6×16.2', np.allclose(f.extents, [60.1, 102.6, TOTAL - SEAM], atol=0.06),
   np.round(f.extents, 2).tolist())

f2 = f.copy()
f2.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
f2.apply_translation([0, 0, TOTAL])
inter = trimesh.boolean.intersection([r, f2], engine=ENG)
iv = inter.volume if inter is not None else 0.0
ok('装配干涉 ≈0', iv < 0.5, f'{iv:.3f} mm³')
asm = uni(r, f2)
ok('装配总高 33.0', abs(asm.bounds[1][2] - TOTAL) < 0.06, f'{asm.bounds[1][2]:.2f}')

def hit(mesh, pts):
    return mesh.contains(np.array(pts, float))

# ① 旧固定孔 ±8.0 已回填 / 旧口已回填
ps = [(0, 50.3, 12.65), (-8.0, 50.3, 12.65), (8.0, 50.3, 12.65), (0, 50.3, 10.0)]
cs = hit(r, ps)
ok('① 旧口 + 旧孔±8.0 已回填', bool(np.all(cs)), cs.astype(int).tolist())

# 新喉口/喇叭口/固定孔/沉头
po = [(0, 50.3, ZC), (0, 51.25, ZC), (0, 51.2, ZC + 2.2),
      (-PITCH, 50.3, ZC), (PITCH, 50.3, ZC), (PITCH, 51.25, ZC)]
co = hit(r, po)
ok('Type-C 新口/喇叭口/孔/沉头 贯通', bool(np.all(~co)), (~co).tolist())

def span_x(mesh, y, z, lim):
    locs, _, _ = mesh.ray.intersects_location([[-40, y, z]], [[1, 0, 0]])
    if len(locs) == 0:
        return None
    xs = locs[:, 0]; xs = xs[np.abs(xs) < lim]
    return np.sort(xs)

s_th = span_x(r, 49.6, ZC, 5.0)
ok('喉口宽 9.0', s_th is not None and len(s_th) == 2 and abs(abs(s_th[-1]) - 4.5) < 0.15,
   None if s_th is None else np.round(s_th, 2).tolist())
s_fl = span_x(r, 51.2, ZC, 5.6)
ok('喇叭口宽 11.0', s_fl is not None and len(s_fl) == 2 and abs(abs(s_fl[-1]) - 5.5) < 0.15,
   None if s_fl is None else np.round(s_fl, 2).tolist())

def zray(mesh, x, y):
    locs, _, _ = mesh.ray.intersects_location([[x, y, -5]], [[0, 0, 1]])
    return np.sort(locs[:, 2]) if len(locs) else np.array([])

# 天线槽（-Y 端壁横向盲槽：挖深 1.2 → 只留 0.8 皮，不透）
def yray(mesh, x, z):
    """只取 -Y 侧命中（射线从 +60 打来，会穿到对面 +Y 端壁，须过滤）"""
    locs, _, _ = mesh.ray.intersects_location([[x, 60, z]], [[0, -1, 0]])
    if len(locs) == 0:
        return np.array([])
    ys = np.sort(locs[:, 1])
    return ys[ys < -40]

ys = yray(r, SLOT_XC, SLOT_ZC)                # 槽中心 → [-51.30, -50.50] 只剩 0.8 皮
ys_lo = yray(r, SLOT_XC - SLOT_L/2 + 0.4, SLOT_ZC)   # 槽内靠左端
ys_hi = yray(r, SLOT_XC + SLOT_L/2 - 0.4, SLOT_ZC)   # 槽内靠右端
ys_uz = yray(r, SLOT_XC, SLOT_ZC + SLOT_H/2 - 0.3)   # 槽内靠上沿
ys_dz = yray(r, SLOT_XC, SLOT_ZC - SLOT_H/2 + 0.3)   # 槽内靠下沿
ox = yray(r, SLOT_XC + SLOT_L/2 + 1.0, SLOT_ZC)      # 槽右外侧 → 实壁 2.0
oz = yray(r, SLOT_XC, SLOT_ZC + SLOT_H/2 + 0.4)      # 槽上外侧 → 实壁 2.0
oz2 = yray(r, SLOT_XC, SLOT_ZC - SLOT_H/2 - 0.4)     # 槽下外侧 → 实壁 2.0
far = yray(r, -10.0, SLOT_ZC)                        # 远处对照 → 实壁 2.0

def is_skin(v):
    return len(v) == 2 and abs(v[0] + 51.3) < 0.06 and abs(v[1] + 50.5) < 0.06

def is_wall(v):
    return len(v) == 2 and abs(v[0] + 51.3) < 0.06 and abs(v[1] + 49.3) < 0.06

ok('④ 天线槽：端壁挖深 1.2 留 0.8 皮（不透）',
   all(is_skin(v) for v in (ys, ys_lo, ys_hi, ys_uz, ys_dz))
   and all(is_wall(v) for v in (ox, oz, oz2, far)),
   f'槽={np.round(ys,2).tolist()} 右外={np.round(ox,2).tolist()} '
   f'上外={np.round(oz,2).tolist()} 下外={np.round(oz2,2).tolist()} 远={np.round(far,2).tolist()}')

# ④ 槽四条边界实测（边界内外各 0.2mm；取槽高/槽长中点避开 R1 圆角）
XL, XR = SLOT_XC - SLOT_L/2, SLOT_XC + SLOT_L/2
ZB, ZT = SLOT_ZC - SLOT_H/2, SLOT_ZC + SLOT_H/2
edge = {
    'x 左界': (yray(r, XL - 0.2, SLOT_ZC), yray(r, XL + 0.2, SLOT_ZC)),
    'x 右界': (yray(r, XR + 0.2, SLOT_ZC), yray(r, XR - 0.2, SLOT_ZC)),
    'z 下界': (yray(r, SLOT_XC, ZB - 0.2), yray(r, SLOT_XC, ZB + 0.2)),
    'z 上界': (yray(r, SLOT_XC, ZT + 0.2), yray(r, SLOT_XC, ZT - 0.2)),
}
ok('④ 槽边界实测：x -0.45~19.55 / z 5.5~8.5',
   all(is_wall(o) and is_skin(i) for o, i in edge.values()),
   ' · '.join(f'{k}外{np.round(o,2).tolist()}内{np.round(i,2).tolist()}'
              for k, (o, i) in edge.items()))

# ⑤ 螺丝头座深度 / 原 M2×9.5 咬合长度
lo = min(POST, key=lambda p: p[1])
zs = zray(r, lo[0] + 1.8, lo[1])                     # r=1.8：⌀5.0 头座内、⌀2.3 过孔外
seat = zs[0] if len(zs) else 0.0
bite = WELL_W + SCREW_L - FACE_W
ok(f'⑤ 头座深 {WELL_W} / 原 M2×9.5 咬合 {bite:.2f}mm',
   abs(seat - WELL_W) < 0.1 and bite >= 3.0, f'座={seat:.2f} 咬合={bite:.2f}')

# 螺丝通道（沿 v4）
for (x, y) in POST:
    locs, _, _ = asm.ray.intersects_location([[x + 0.3, y, -5]], [[0, 0, 1]])
    zs = np.sort(locs[:, 2]) if len(locs) else np.array([])
    ok(f'柱({x:+.2f},{y:+.2f}) 螺丝通道贯通至底孔底',
       len(zs) == 2 and abs(zs[0] - PILOT_W1) < 0.3 and abs(zs[1] - TOTAL) < 0.1,
       np.round(zs, 2).tolist())

pr_s = [(x + 2.5, y, 18.0) for (x, y) in POST]
pr_v = [(x + 1.0, y, 18.0) for (x, y) in POST]
sr, vr = hit(r, pr_s), hit(r, pr_v)
ok('后柱加长段实体 / 通孔空', bool(np.all(sr) and np.all(~vr)),
   f'实体={sr.astype(int).tolist()} 孔={vr.astype(int).tolist()}')

# ② 沿口：竖向实测厚度（射线，contains 在薄区不可靠）
zs = zray(f2, 26.0, 0.0)
rim = zs[-1] - zs[-2] if len(zs) >= 2 else 0.0
ok('② 沿口总厚 ≥1.15（原 0.80）', rim > 1.15, f'{rim:.2f}mm')
ok('② 沿口下沿 = 31.8（原 32.2）',
   len(zs) == 2 and abs(zs[0] - LIP_SEAT_W) < 0.06 and abs(zs[1] - TOTAL) < 0.06,
   np.round(zs, 2).tolist())
xs = span_x(f2, 0.0, 32.98, 27.0)
ok('② 正面开口 50.56（斜边顶）',
   xs is not None and len(xs) == 2 and abs(abs(xs[0]) - WIN_W/2) < 0.06,
   None if xs is None else np.round(xs, 2).tolist())
xs = span_x(f2, 0.0, 32.8, 27.0)
ok('② 斜边内倾 45°×0.4（z=32.8 中点 ±25.08）',
   xs is not None and len(xs) == 2 and abs(abs(xs[0]) - (WIN_W/2 - CHAM/2)) < 0.06,
   None if xs is None else np.round(xs, 2).tolist())
xs = span_x(f2, 0.0, 32.0, 27.0)
ok('② 直壁口径 49.76（z=32.0，内收 0.4 遮黑边）',
   xs is not None and len(xs) == 2 and abs(abs(xs[0]) - (WIN_W/2 - CHAM)) < 0.06,
   None if xs is None else np.round(xs, 2).tolist())
ok('② 窗口中心贯通（无多料）', len(zray(f2, 0.0, 0.0)) == 0,
   np.round(zray(f2, 0.0, 0.0), 2).tolist())

print('=' * 70)
print(f'结果: {sum(res)}/{len(res)} 通过')
print('待确认: ②正面斜边观感 · ④槽位（-Y 短边框内壁, 起点距 +X 长边 10.5, 中心距底 7.0）')
