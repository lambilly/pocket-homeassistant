# 来源: 会话归档 jsonl line 189（3211 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from trimesh.transformations import rotation_matrix

def make_prism(geom2d_xz, y0, y1):
    pr = trimesh.creation.extrude_polygon(geom2d_xz, height=abs(y1-y0))
    pr.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))
    pr.apply_translation([0, max(y0,y1), 0])
    return pr

def rrect(w, h, r):
    """proper rounded rectangle centered at origin in (x,z)"""
    x0,x1,z0,z1 = -w/2, w/2, -h/2, h/2
    hbar = sbox(x0+r, z0, x1-r, z1)
    vbar = sbox(x0, z0+r, x1, z1-r)
    discs = [Point(cx,cz).buffer(r, resolution=32) for cx in (x0+r,x1-r) for cz in (z0+r,z1-r)]
    return unary_union([hbar, vbar]+discs)

W,H,R = 9.0, 3.3, 1.0
ZC = 26.8-5.0-H/2
rr = rrect(W,H,R).buffer(0)   # clean
print("rrect bounds:", [round(v,3) for v in rr.bounds], "expect ±4.5 / ±1.65")

m = trimesh.load('rear.stl')
b1 = trimesh.creation.box(bounds=[[-5.05,-51.30,0.0],[5.05,-49.29,6.8]])
b2 = trimesh.creation.box(bounds=[[-30.05,-6.45,0.0],[-28.04,11.15,6.8]])
m = trimesh.boolean.union([m,b1,b2], engine='manifold')

sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops=[d[:,:2] for d in sec.discrete if np.allclose(d[0],d[-1])]
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(Polygon(l), height=20.2) for l in loops])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m,ext], engine='manifold')

pr = make_prism(rr, 48.0, 51.6)
print("typec prism bounds:", np.round(pr.bounds,3).tolist())
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
print("exported rear_v2.stl")

# ---- re-verify Type-C ----
for z in np.arange(18.2, 22.2, 0.2):
    o=np.array([[0.0,48.0,z]]); d=np.array([[0,1,0.]])
    l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
    print(f"x=0 z={z:5.2f}: {'OPEN' if not len(l) else 'mat @'+str(round(l[0][1],2))}")
# corner check
for cx,cz in [(-3.5,19.5),(3.5,21.8),(0,21.0)]:
    o=np.array([[cx,48.0,cz]]); d=np.array([[0,1,0.]])
    l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
    print(f"corner ({cx},{cz}): {'OPEN' if not len(l) else 'mat'}")
EOF