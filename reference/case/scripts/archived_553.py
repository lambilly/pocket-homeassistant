# 来源: 会话归档 jsonl line 553（3598 字符 Bash heredoc）
cd "D:/Desktop/HA Monitor Display 外壳" && cat > /tmp/f10.py <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from trimesh.creation import extrude_polygon

o = trimesh.load("01_原版/front.stl", force='mesh')

# 1) 取原前壳 z=5.0 截面的裙边环 (外 30.05/51.3 圆角矩形, 内 28.05/49.3)
sec = o.section(plane_origin=[0,0,5.0], plane_normal=[0,0,1])
segs=[]
for line in sec.discrete:
    for a,b in zip(line[:,:2], line[1:,:2]):
        segs.append(__import__('shapely.geometry',fromlist=['LineString']).LineString([tuple(a),tuple(b)]))
from shapely.ops import polygonize
polys=sorted(polygonize(unary_union(segs)), key=lambda p:-p.area)
ring = polys[0]   # 裙边环(带内孔)
assert ring.area > 500 and len(ring.interiors)==1, (ring.area, len(ring.interiors))
inner = list(ring.interiors)[0]
print("环面积", round(ring.area,2), "内环bbox", np.round(inner.bounds,1).tolist())

# 2) 两段拉伸
ringA = Polygon(ring.exterior, [inner]);                       eA = extrude_polygon(ringA, 20.6); eA.apply_translation([0,0,5.0])   # 5.0→25.6
ringB = Polygon(ring.exterior, [inner.buffer(0.15)]);          eB = extrude_polygon(ringB, 0.6);  eB.apply_translation([0,0,25.6])  # 25.6→26.2

# 3) 角柱延长 ⌀2.9 (6.5→26.9, 与原柱重叠对接)
posts=[]
for sx in (1,-1):
    for sy in (1,-1):
        c=trimesh.creation.cylinder(radius=2.9/2, height=20.4, sections=64)
        c.apply_translation([sx*24.75, sy*46, 16.7])  # 6.5..26.9
        posts.append(c)

ext = trimesh.boolean.union([eA,eB]+posts, engine='manifold')

# 4) 开孔: Type-C 9.0x3.3 R1.0 @z18.7-22.0 (-Y壁) + 2x⌀2.5 @x=±8 + 4x⌀1.55 导向孔 22.35..26.9
pr = unary_union([sbox(-3.5,19.7,3.5,21.0).union(Polygon([(x,18.7) for x in ()]) if False else sbox(-4.5,18.7,-2.5,22.0)).buffer(0) for x in []])
tc2d = sbox(-4.5,18.7,4.5,22.0)  # 先方角, 再四角圆
tc2d = unary_union([sbox(-3.5,18.7,3.5,22.0), sbox(-4.5,19.7,4.5,21.0)] +
                   [Polygon([(cx+1.0*np.cos(t*np.pi/2), 20.35+1.0*np.sin(t*np.pi/2)) for t in range(4)]).buffer(0.001) for cx in (-3.5,3.5) for _ in [0]] )
# 更简单: 圆角矩形 = 横条+竖条+四角圆
import math
tc2d = unary_union([sbox(-3.5,18.7,3.5,22.0), sbox(-4.5,19.35,4.5,21.35)] +
                   [Point(c).buffer(1.0) for c in [(-3.5,19.7),(-3.5,21.0),(3.5,19.7),(3.5,21.0)]])
from shapely.geometry import Point
tc2d = unary_union([sbox(-3.5,18.7,3.5,22.0), sbox(-4.5,19.7,4.5,21.0)] +
                   [Point(c).buffer(1.0, quad_segs=32) for c in [(-3.5,19.7),(-3.5,21.0),(3.5,19.7),(3.5,21.0)]])
tcc = extrude_polygon(Polygon(tc2d.exterior), 7.0); tcc.apply_transform(
    np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],dtype=float))   # (x,y,z)->(x,-z,y)
tcc.apply_translation([0, -45.5, 0])   # y: -6..0 -> -51.5..-45.5
holes=[]
for x0 in (-8.0, 8.0):
    c=trimesh.creation.cylinder(radius=1.25, height=8.0, sections=48)
    c.apply_transform(np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],dtype=float))
    c.apply_translation([x0, -49.8, 20.35]); holes.append(c)
guides=[]
for sx in (1,-1):
    for sy in (1,-1):
        g=trimesh.creation.cylinder(radius=1.55/2, height=5.5, sections=48)
        g.apply_translation([sx*24.75, sy*46, 24.9])  # 22.15..27.65 → 覆盖 22.35..26.9
        guides.append(g)
ext = trimesh.boolean.difference([ext, tcc]+holes+guides, engine='manifold')

# 5) 与原前壳对接
v3 = trimesh.boolean.union([o, ext], engine='manifold')
print("front_v3: watertight",v3.is_watertight,"bodies",len(v3.split(only_watertight=False)),
      "bbox",np.round(v3.bounds,2).tolist(),"vol",round(v3.volume,1),"tris",len(v3.faces))
v3.export("03_v2_前壳加高20/front_v3.stl")
EOF
python /tmp/f10.py 2>&1 | grep -v Warning