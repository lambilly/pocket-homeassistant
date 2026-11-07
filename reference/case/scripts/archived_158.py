# 来源: 会话归档 jsonl line 158（3805 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from trimesh.transformations import rotation_matrix

m = trimesh.load('rear.stl')
print("start:", m.is_watertight, np.round(m.extents,3))

# ---------- 1) fill -Y short-edge notch (top 4.8 -> 6.8) ----------
b1 = trimesh.creation.box(bounds=[[-5.05, -51.30, 0.0], [5.05, -49.29, 6.8]])
# ---------- 2) fill -X long-edge notch / TF slot (top 3.95 -> 6.8) ----------
b2 = trimesh.creation.box(bounds=[[-30.05, -6.45, 0.0], [-28.04, 11.15, 6.8]])
m = trimesh.boolean.union([m, b1, b2], engine='manifold')
print("notches filled:", m.is_watertight, np.round(m.extents,3))

# ---------- 3) extend rim by +20mm (6.8 -> 26.8) ----------
Z_NEW = 26.8
sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops = [Polygon(d[:,:2]) for d in sec.discrete if np.allclose(d[0], d[-1])]
merged = unary_union(loops)
polys = list(merged.geoms) if merged.geom_type=='MultiPolygon' else [merged]
print("slice polys:", len(polys), "rings:", [1+len(p.interiors) for p in polys])
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(p, height=Z_NEW-6.6) for p in polys])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m, ext], engine='manifold')
print("extended:", m.is_watertight, np.round(m.extents,3))

# ---------- 4) Type-C opening on +Y edge ----------
# 9.0 x 3.3 mm, R1.0, top edge 5mm below rim top -> z 18.5..21.8, centered x=0
W,H,R = 9.0, 3.3, 1.0
ZC = 26.8 - 5.0 - H/2      # 20.15
def rounded_rect(w,h,r):
    x0,x1,y0,y1 = -w/2, w/2, -h/2, h/2
    s = sbox(x0+r, y0+r, x1-r, y1-r)
    from shapely.geometry import Point
    discs = [Point(x,y).buffer(r, resolution=16) for x in (x0+r,x1-r) for y in (y0+r,y1-r)]
    return unary_union([s]+discs)
# polygon in (x, -z) plane, extrude 3.6 along +Z then rotate -90 about X -> (x, w, z)
poly = rounded_rect(W,H,R)
poly = trimesh.transformations.transform_points  # noop ref
prism = trimesh.creation.extrude_polygon(poly, height=3.6)
# extrude_polygon: polygon (u,v) -> world (u,v,w) with w=0..3.6
# rotate -90 about X: (u,v,w)->(u,w,-v). we want world z = ZC + v  => build with v = z-ZC ; use -v mapping
R_neg = rotation_matrix(-np.pi/2, [1,0,0])
prism.apply_transform(R_neg)              # now (u, w, -v)
prism.apply_translation([0, 48.0, ZC])    # y: 48..51.6 ; z: ZC + v
print("typec prism bounds:", np.round(prism.bounds,3).tolist())
m = trimesh.boolean.difference([m, prism], engine='manifold')

# ---------- 5) two ⌀2.5 holes at x=±8, z=ZC ----------
for sx in (-8.0, 8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))   # axis Z -> Y
    cyl.apply_translation([sx, 48.0+1.8, ZC])
    m = trimesh.boolean.difference([m, cyl], engine='manifold')
print("typec+holes cut:", m.is_watertight, np.round(m.extents,3))

# ---------- 6) four corner screw columns ----------
for sx in (-24.75, 24.75):
    for sy in (-46.0, 46.0):
        col = trimesh.creation.cylinder(radius=3.0, height=26.8-2.5, sections=64)
        col.apply_translation([sx, sy, 2.5 + (26.8-2.5)/2])
        m = trimesh.boolean.union([m, col], engine='manifold')
        bore = trimesh.creation.cylinder(radius=1.15, height=27.2, sections=48)
        bore.apply_translation([sx, sy, 13.5])
        m = trimesh.boolean.difference([m, bore], engine='manifold')
        cb = trimesh.creation.cylinder(radius=2.1, height=2.8, sections=48)
        cb.apply_translation([sx, sy, 25.4])   # 24.0..26.8
        m = trimesh.boolean.difference([m, cb], engine='manifold')
print("columns done:", m.is_watertight, np.round(m.extents,3))

m.export('rear_v2.stl')
print("exported rear_v2.stl faces:", len(m.faces))
EOF