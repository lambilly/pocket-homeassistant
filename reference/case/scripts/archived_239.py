# 来源: 会话归档 jsonl line 239（5113 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely.affinity import translate as strans
from trimesh.transformations import rotation_matrix
import matplotlib; matplotlib.use('Agg')
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

def make_prism(geom2d_xz, y0, y1, zc):
    pr = trimesh.creation.extrude_polygon(geom2d_xz, height=abs(y1-y0))
    pr.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))
    pr.apply_translation([0, max(y0,y1), zc])
    return pr

def rrect(w, h, r):
    x0,x1,y0,y1 = -w/2, w/2, -h/2, h/2
    return unary_union([sbox(x0+r, y0, x1-r, y1), sbox(x0, y0+r, x1, y1-r)]
        + [Point(cx,cy).buffer(r, resolution=32) for cx in (x0+r,x1-r) for cy in (y0+r,y1-r)])

m = trimesh.load('rear.stl')

# 1) fill notches
b1 = trimesh.creation.box(bounds=[[-5.05,-51.30,0.0],[5.05,-49.29,6.8]])
b2 = trimesh.creation.box(bounds=[[-30.05,-6.45,0.0],[-28.04,11.15,6.8]])
m = trimesh.boolean.union([m,b1,b2], engine='manifold')

# 2) fill thin-floor pocket
slab = trimesh.creation.box(bounds=[[-27.0,-42.5,0.9],[-0.6,-0.6,2.5]])
m = trimesh.boolean.union([m,slab], engine='manifold')

# 3) extend rim
sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops=[d[:,:2] for d in sec.discrete if np.allclose(d[0],d[-1])]
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(Polygon(l), height=20.2) for l in loops])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m,ext], engine='manifold')
print("base+rim:", m.is_watertight, np.round(m.extents,3))

# 4) full rib grid
ribs=[]
for xc in [-24,-12,0,12,24]:
    ribs.append(trimesh.creation.box(bounds=[[xc-0.5,-49.4,2.0],[xc+0.5,49.4,3.5]]))
for yc in [-36,-24,-12,0,12,24,36]:
    ribs.append(trimesh.creation.box(bounds=[[-28.1,yc-0.5,2.0],[28.1,yc+0.5,3.5]]))
m = trimesh.boolean.union([m]+ribs, engine='manifold')
print("rib grid:", m.is_watertight)

# 5) corner columns
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        col = trimesh.creation.cylinder(radius=3.0, height=24.3, sections=64)
        col.apply_translation([sx,sy,2.5+24.3/2])
        m = trimesh.boolean.union([m,col], engine='manifold')
print("columns:", m.is_watertight)

# 6) embossed text: recessed panel 0.8 deep on bottom face (z=0), letters raised flush to z=0
S = 48.0/10.7147
tp = TextPath((0,0), "HA Monitor Display", size=S, prop=FontProperties(family='DejaVu Sans', weight='bold'))
contours=[p.copy() for p in tp.to_polygons()]
for c in contours: c[:,0] *= -1          # mirror for outside viewing from -z
ps=[Polygon(c) for c in contours]; ps=[p for p in ps if p.is_valid and p.area>1e-9]
depth={i: sum(1 for j,q in enumerate(ps) if j!=i and q.contains(p.representative_point())) for i,p in enumerate(ps)}
gpoly=[]
for i,p in enumerate(ps):
    if depth[i]%2==0:
        holes=[q.exterior.coords for j,q in enumerate(ps) if depth[j]%2==1 and q.within(p)]
        gpoly.append(orient(Polygon(p.exterior.coords, holes)))
allg=unary_union(gpoly)
minx,miny,maxx,maxy=allg.bounds
allg=strans(allg, xoff=-(minx+maxx)/2, yoff=-(miny+maxy)/2)
print("text bounds:", np.round(allg.bounds,2).tolist())
bx0,by0,bx1,by1 = allg.bounds
PW,PH,PR = (bx1-bx0)+5.0, (by1-by0)+5.0, 2.0
panel3d = trimesh.creation.extrude_polygon(orient(rrect(PW,PH,PR).buffer(0)), height=0.81)  # z 0..0.81
txt3d = trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, height=0.8) for g in
                                  (allg.geoms if allg.geom_type=='MultiPolygon' else [allg])])
m = trimesh.boolean.difference([m, panel3d], engine='manifold')
m = trimesh.boolean.union([m, txt3d], engine='manifold')
print("text panel:", m.is_watertight, "extents", np.round(m.extents,3))

# 7) Type-C opening: lower edge 5.5mm above bottom face -> z 5.5..8.8, center 7.15
W,H,R = 9.0,3.3,1.0
ZC = 7.15
pr = make_prism(rrect(W,H,R).buffer(0), 48.0, 51.6, ZC)
assert np.allclose(pr.bounds, [[-4.5,48.0,ZC-H/2],[4.5,51.6,ZC+H/2]], atol=0.01), pr.bounds
m = trimesh.boolean.difference([m, pr], engine='manifold')
for sx in (-8.0,8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2,[1,0,0]))
    cyl.apply_translation([sx, 49.8, ZC])
    m = trimesh.boolean.difference([m,cyl], engine='manifold')
print("type-c:", m.is_watertight)

# 8) corner bores + counterbores (drill last)
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        bore = trimesh.creation.cylinder(radius=1.15, height=27.4, sections=48)
        bore.apply_translation([sx,sy,13.4])
        m = trimesh.boolean.difference([m,bore], engine='manifold')
        cb = trimesh.creation.cylinder(radius=2.1, height=2.8, sections=48)
        cb.apply_translation([sx,sy,25.4])
        m = trimesh.boolean.difference([m,cb], engine='manifold')

print("FINAL:", m.is_watertight, "extents", np.round(m.extents,3), "volume", round(m.volume,1))
m.export('rear_v3.stl')
print("exported rear_v3.stl")
EOF