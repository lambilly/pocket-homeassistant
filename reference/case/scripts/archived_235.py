# 来源: 会话归档 jsonl line 235（4296 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely.affinity import scale as sscale, translate as strans
from trimesh.transformations import rotation_matrix
import matplotlib; matplotlib.use('Agg')
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

def make_prism(geom2d_xz, y0, y1, zc):
    """polygon in (x,z) centered at origin, extruded along y, centered at zc"""
    pr = trimesh.creation.extrude_polygon(geom2d_xz, height=abs(y1-y0))
    pr.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))   # (x,y,w)->(x,-w,y)
    pr.apply_translation([0, max(y0,y1), zc])
    return pr

def rrect(w, h, r):
    x0,x1,z0,z1 = -w/2, w/2, -h/2, h/2
    return unary_union([sbox(x0+r, z0, x1-r, z1), sbox(x0, z0+r, x1, z1-r)]
        + [Point(cx,cz).buffer(r, resolution=32) for cx in (x0+r,x1-r) for cz in (z0+r,z1-r)])

m = trimesh.load('rear.stl')

# ---- 1) fill both edge notches ----
b1 = trimesh.creation.box(bounds=[[-5.05,-51.30,0.0],[5.05,-49.29,6.8]])
b2 = trimesh.creation.box(bounds=[[-30.05,-6.45,0.0],[-28.04,11.15,6.8]])
m = trimesh.boolean.union([m,b1,b2], engine='manifold')

# ---- 2) fill the thin-floor pocket (x -26.95..-0.65, y -42.45..-0.65, floor 1.0) ----
slab = trimesh.creation.box(bounds=[[-27.0,-42.5,0.9],[-0.6,-0.6,2.5]])
m = trimesh.boolean.union([m,slab], engine='manifold')
print("notches+pocket filled:", m.is_watertight)

# ---- 3) extend rim 6.8 -> 26.8 ----
sec = m.section(plane_origin=[0,0,6.6], plane_normal=[0,0,1])
loops=[d[:,:2] for d in sec.discrete if np.allclose(d[0],d[-1])]
ext = trimesh.util.concatenate([trimesh.creation.extrude_polygon(Polygon(l), height=20.2) for l in loops])
ext.apply_translation([0,0,6.6])
m = trimesh.boolean.union([m,ext], engine='manifold')
print("rim extended:", m.is_watertight, np.round(m.extents,3))

# ---- 4) full rib grid: 12mm pitch, 1mm wide, top 3.5 ----
ribs=[]
for xc in [-24,-12,0,12,24]:
    ribs.append(trimesh.creation.box(bounds=[[xc-0.5,-49.4,2.0],[xc+0.5,49.4,3.5]]))
for yc in [-36,-24,-12,0,12,24,36]:
    ribs.append(trimesh.creation.box(bounds=[[-28.1,yc-0.5,2.0],[28.1,yc+0.5,3.5]]))
m = trimesh.boolean.union([m]+ribs, engine='manifold')
print("rib grid:", m.is_watertight)

# ---- 5) corner screw columns ----
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        col = trimesh.creation.cylinder(radius=3.0, height=24.3, sections=64)
        col.apply_translation([sx,sy,2.5+24.3/2])
        m = trimesh.boolean.union([m,col], engine='manifold')
print("columns:", m.is_watertight)

# ---- 6) embossed text on outer bottom face ----
S = 48.0/10.7147     # font size so text width = 48mm
tp = TextPath((0,0), "HA Monitor Display", size=S, prop=FontProperties(family='DejaVu Sans', weight='bold'))
contours = [p.copy() for p in tp.to_polygons()]
# mirror in x (text viewed from outside/bottom = -z side) 
for c in contours: c[:,0] *= -1
ps = [Polygon(c) for c in contours]
ps = [p for p in ps if p.is_valid and p.area>1e-9]
depth = {i: sum(1 for j,q in enumerate(ps) if j!=i and q.contains(p.representative_point())) for i,p in enumerate(ps)}
gpoly=[]
for i,p in enumerate(ps):
    if depth[i]%2==0:
        holes=[q.exterior.coords for j,q in enumerate(ps) if depth[j]%2==1 and q.within(p)]
        gpoly.append(orient(Polygon(p.exterior.coords, holes)))
allg = unary_union(gpoly)
minx,miny,maxx,maxy = allg.bounds
allg = strans(allg, xoff=-(minx+maxx)/2, yoff=-(miny+maxy)/2)   # center at (0,0)
print("text bounds:", np.round(allg.bounds,2).tolist())
txt = trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, height=0.8) for g in
                                 (allg.geoms if allg.geom_type=='MultiPolygon' else [allg])])
# panel = text bbox + 2.5 margin, rounded corners r2, recessed 0.8 into bottom face
bx0,by0,bx1,by1 = allg.bounds
panel2d = rrect((bx1-bx0)+5.0, (by1-by0)+5.0, 2.0).buffer(0)
panel = make_prism(panel2d, -55, 55, 0)   # y span covers whole part; centered z=0 -> z -3.3..3.3, cut only removes
m = trimesh.boolean.difference([m, panel], engine='manifold')   # cuts z<3.3 !! wrong - fix below
print("TEMP wrong panel cut - rebuilding")
EOF