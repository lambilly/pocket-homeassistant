# 来源: 会话归档 jsonl line 166（4986 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from trimesh.transformations import rotation_matrix

def polys_with_holes(loops):
    """Build shapely polygons from closed loops, nesting odd-depth loops as holes."""
    ps = [Polygon(l) for l in loops if len(l) >= 4]
    ps = [p for p in ps if p.is_valid and p.area > 1e-6]
    depth = {}
    for i, p in enumerate(ps):
        depth[i] = sum(1 for j, q in enumerate(ps) if j != i and q.contains(p.representative_point()))
    outers = [(i, p) for i, p in enumerate(ps) if depth[i] % 2 == 0]
    holes  = [(i, p) for i, p in enumerate(ps) if depth[i] % 2 == 1]
    result = []
    for i, p in outers:
        hs = [h.exterior.coords for k, h in holes
              if p.contains(h.representative_point()) and
              min((sum(1 for _, q in outers if q.contains(h.representative_point()) and q.area < p.area),), default=0) is not None
              and not any(q.contains(h.representative_point()) and q.area < p.area for _, q in outers)]
        result.append(Polygon(p.exterior.coords, hs))
    return result

m = trimesh.load('rear.stl')

# 1) fill -Y short notch + 2) fill -X long notch(TF slot)
b1 = trimesh.creation.box(bounds=[[-5.05, -51.30, 0.0], [5.05, -49.29, 6.8]])
b2 = trimesh.creation.box(bounds=[[-30.05, -6.45, 0.0], [-28.04, 11.15, 6.8]])
m = trimesh.boolean.union([m, b1, b2], engine='manifold')
print("1-2 notches filled:", m.is_watertight, np.round(m.extents,3))

# 3) extend rim +20mm using z=6.6 cross-section (with inner hole preserved)
sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops = [d[:,:2] for d in sec.discrete if np.allclose(d[0], d[-1])]
print("loops:", len(loops), "areas:", [round(Polygon(l).area,1) for l in loops])
polys = polys_with_holes(loops)
print("polys:", len(polys), "rings:", [1+len(p.interiors) for p in polys])
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(orient(p), height=26.8-6.6) for p in polys])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m, ext], engine='manifold')
print("3 extended:", m.is_watertight, np.round(m.extents,3), "volume", round(m.volume,1))
# sanity: must still be open (ray at center hits interior floor, not rim top)
o=np.array([[0,0,60.]]); d=np.array([[0,0,-1.]])
l,_,_=m.ray.intersects_location(o,d,multiple_hits=False)
print("   ray (0,0) top hit:", round(l[0][2],2) if len(l) else None, "(expect ~3.5, NOT 26.8)")
assert len(l) and l[0][2] < 10, "rim extension capped the part!"

# 4) Type-C opening: 9.0 x 3.3, R1.0, top edge 5mm below rim top -> z 18.5~21.8
W,H,R = 9.0, 3.3, 1.0
Z_TOP_RIM = 26.8
ZC = Z_TOP_RIM - 5.0 - H/2
x0,x1,y0,y1 = -W/2, W/2, -H/2, H/2
core = sbox(x0+R, y0+R, x1-R, y1-R)
discs = [Point(cx,cy).buffer(R, resolution=24) for cx in (x0+R, x1-R) for cy in (y0+R, y1-R)]
rr = unary_union([core]+discs)
# map into (x, -z) coords then extrude along +Z, rotate -90 about X => (x, w, z)
rr_local = trimesh.transformations.transform_points(np.array(rr.exterior.coords), np.eye(4)) if False else None
from shapely.affinity import scale as sscale, translate as strans
rr_plane = sscale(rr, yfact=-1.0)          # (x, z) -> (x, -z)
rr_plane = strans(rr_plane, yoff=ZC)       # v = ZC - z  ... then -90 rotation: world z = -(v) = z-ZC
prism = trimesh.creation.extrude_polygon(rr_plane, height=3.6)
prism.apply_transform(rotation_matrix(-np.pi/2, [1,0,0]))
prism.apply_translation([0, 48.0, 0.0])
print("4 typec prism bounds:", np.round(prism.bounds,3).tolist(), "(expect y 48~51.6, z 18.5~21.8)")
m = trimesh.boolean.difference([m, prism], engine='manifold')

# 5) two ⌀2.5 holes, x=±8, z=ZC, through wall
for sx in (-8.0, 8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))
    cyl.apply_translation([sx, 49.8, ZC])
    m = trimesh.boolean.difference([m, cyl], engine='manifold')
print("5 typec+holes:", m.is_watertight, np.round(m.extents,3))

# 6) four corner screw columns ⌀6 + ⌀2.3 through bore + ⌀4.2x2.5 counterbore
for sx in (-24.75, 24.75):
    for sy in (-46.0, 46.0):
        col = trimesh.creation.cylinder(radius=3.0, height=24.3, sections=64)
        col.apply_translation([sx, sy, 2.5+24.3/2])
        m = trimesh.boolean.union([m, col], engine='manifold')
        bore = trimesh.creation.cylinder(radius=1.15, height=27.4, sections=48)
        bore.apply_translation([sx, sy, 13.4])
        m = trimesh.boolean.difference([m, bore], engine='manifold')
        cb = trimesh.creation.cylinder(radius=2.1, height=2.8, sections=48)
        cb.apply_translation([sx, sy, 25.4])
        m = trimesh.boolean.difference([m, cb], engine='manifold')
print("6 columns:", m.is_watertight, np.round(m.extents,3), "volume", round(m.volume,1))

m.export('rear_v2.stl')
print("exported rear_v2.stl faces:", len(m.faces))
EOF