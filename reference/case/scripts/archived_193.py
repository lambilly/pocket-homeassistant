# 来源: 会话归档 jsonl line 193（3501 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from trimesh.transformations import rotation_matrix

def make_prism(geom2d_xz, y0, y1, zc):
    pr = trimesh.creation.extrude_polygon(geom2d_xz, height=abs(y1-y0))
    pr.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))   # (x,y,z)->(x,-z,y): world z = polygon v
    pr.apply_translation([0, max(y0,y1), zc])
    return pr

def rrect(w, h, r):
    x0,x1,z0,z1 = -w/2, w/2, -h/2, h/2
    return unary_union([sbox(x0+r, z0, x1-r, z1), sbox(x0, z0+r, x1, z1-r)]
        + [Point(cx,cz).buffer(r, resolution=32) for cx in (x0+r,x1-r) for cz in (z0+r,z1-r)])

W,H,R = 9.0, 3.3, 1.0
ZC = 26.8-5.0-H/2
m = trimesh.load('rear.stl')
b1 = trimesh.creation.box(bounds=[[-5.05,-51.30,0.0],[5.05,-49.29,6.8]])
b2 = trimesh.creation.box(bounds=[[-30.05,-6.45,0.0],[-28.04,11.15,6.8]])
m = trimesh.boolean.union([m,b1,b2], engine='manifold')

sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops=[d[:,:2] for d in sec.discrete if np.allclose(d[0],d[-1])]
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(Polygon(l), height=20.2) for l in loops])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m,ext], engine='manifold')
print("extended:", m.is_watertight, np.round(m.extents,3))

pr = make_prism(rrect(W,H,R).buffer(0), 48.0, 51.6, ZC)
print("typec prism bounds:", np.round(pr.bounds,3).tolist())
assert np.allclose(pr.bounds, [[-4.5,48.0,ZC-H/2],[4.5,51.6,ZC+H/2]], atol=0.01), "prism wrong"
m = trimesh.boolean.difference([m, pr], engine='manifold')

for sx in (-8.0,8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2,[1,0,0]))
    cyl.apply_translation([sx, 49.8, ZC])
    m = trimesh.boolean.difference([m,cyl], engine='manifold')

for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        col = trimesh.creation.cylinder(radius=3.0, height=24.3, sections=64)
        col.apply_translation([sx,sy,2.5+24.3/2])
        m = trimesh.boolean.union([m,col], engine='manifold')
        bore = trimesh.creation.cylinder(radius=1.15, height=27.4, sections=48)
        bore.apply_translation([sx,sy,13.4])
        m = trimesh.boolean.difference([m,bore], engine='manifold')
        cb = trimesh.creation.cylinder(radius=2.1, height=2.8, sections=48)
        cb.apply_translation([sx,sy,25.4])
        m = trimesh.boolean.difference([m,cb], engine='manifold')

print("final:", m.is_watertight, "extents", np.round(m.extents,3), "volume", round(m.volume,1))
m.export('rear_v2.stl')
print("exported")

print("\n--- Type-C verification (x=0, expect OPEN z 18.6~21.6, mat outside) ---")
for z in [17.5,18.4,18.6,19.5,20.15,21.0,21.6,21.8,22.5]:
    o=np.array([[0.0,48.0,z]]); d=np.array([[0,1,0.]])
    l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
    print(f"z={z:5.2f}: {'OPEN' if not len(l) else 'mat @y='+str(round(l[0][1],2))}")
print("--- ⌀2.5 holes (expect OPEN) ---")
for sx in (-8,8):
    o=np.array([[sx,48.0,ZC]]); d=np.array([[0,1,0.]])
    l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
    print(f"x={sx}: {'OPEN' if not len(l) else 'mat'}")
print("--- plate integrity under +Y edge (z=1.0 expect MATERIAL) ---")
o=np.array([[0.0,50.0,1.0]]); d=np.array([[0,1,0.]])
l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
print("z=1.0:", 'mat @'+str([round(v[1],2) for v in l]))
EOF