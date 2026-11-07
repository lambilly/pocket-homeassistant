# 来源: 会话归档 jsonl line 347（3767 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from trimesh.transformations import rotation_matrix

def make_prism(geom2d_xz, y0, y1, zc):
    pr = trimesh.creation.extrude_polygon(geom2d_xz, height=abs(y1-y0))
    pr.apply_transform(rotation_matrix(np.pi/2, [1,0,0]))
    pr.apply_translation([0, max(y0,y1), zc])
    return pr
def rrect(w,h,r):
    x0,x1,y0,y1 = -w/2,w/2,-h/2,h/2
    return unary_union([sbox(x0+r,y0,x1-r,y1), sbox(x0,y0+r,x1,y1-r)]
        + [Point(cx,cy).buffer(r,resolution=32) for cx in (x0+r,x1-r) for cy in (y0+r,y1-r)])

m = trimesh.load('rear.stl')

# 1) fill thin-floor pocket
slab = trimesh.creation.box(bounds=[[-27.0,-42.5,0.9],[-0.6,-0.6,2.5]])
m = trimesh.boolean.union([m,slab], engine='manifold')

# 2) full rib grid
ribs=[]
for xc in [-24,-12,0,12,24]:
    ribs.append(trimesh.creation.box(bounds=[[xc-0.5,-49.4,2.0],[xc+0.5,49.4,3.5]]))
for yc in [-36,-24,-12,0,12,24,36]:
    ribs.append(trimesh.creation.box(bounds=[[-28.1,yc-0.5,2.0],[28.1,yc+0.5,3.5]]))
m = trimesh.boolean.union([m]+ribs, engine='manifold')
print("floor+grid:", m.is_watertight)

# 3) trim above 3.7 and rebuild wall as ONE extrusion (no notches, seamless)
sec0 = m.section(plane_origin=[0,0,3.7], plane_normal=[0,0,1])
loops = sorted([d[:,:2] for d in sec0.discrete if np.allclose(d[0],d[-1])],
               key=lambda l: Polygon(l).area, reverse=True)
from shapely.geometry.polygon import orient
ring = orient(Polygon(loops[0], [loops[1]]).buffer(0))
cutter = trimesh.creation.box(bounds=[[-60,-80,3.7],[60,80,60]])
m = trimesh.boolean.difference([m, cutter], engine='manifold')
wall = trimesh.creation.extrude_polygon(ring, height=26.8-3.7)
wall.apply_translation([0,0,3.7])
m = trimesh.boolean.union([m, wall], engine='manifold')
print("wall:", m.is_watertight, np.round(m.extents,3), "parts", len(m.split(only_watertight=False)))

# 4) corner columns D6.8, z 2.4..26.8
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        col = trimesh.creation.cylinder(radius=3.4, height=24.4, sections=64)
        col.apply_translation([sx,sy,2.4+12.2])
        m = trimesh.boolean.union([m,col], engine='manifold')
print("columns:", m.is_watertight, "parts", len(m.split(only_watertight=False)))

# 5) Type-C opening z 5.5~8.8 + two D2.5 holes at z=7.15 (unchanged)
W,H,R,ZC = 9.0,3.3,1.0,7.15
pr = make_prism(rrect(W,H,R).buffer(0), 48.0, 51.6, ZC)
assert np.allclose(pr.bounds, [[-4.5,48.0,ZC-H/2],[4.5,51.6,ZC+H/2]], atol=0.01)
m = trimesh.boolean.difference([m, pr], engine='manifold')
for sx in (-8.0,8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2,[1,0,0]))
    cyl.apply_translation([sx, 49.8, ZC])
    m = trimesh.boolean.difference([m,cyl], engine='manifold')
print("type-c:", m.is_watertight)

# 6) corner screw path (from bottom face):
#    head well D4.6 x 21.5 deep  +  clearance D2.3 up through top
WELL_D, WELL_TOP = 4.6, 21.5
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        well = trimesh.creation.cylinder(radius=WELL_D/2, height=WELL_TOP, sections=64)
        well.apply_translation([sx,sy,WELL_TOP/2])
        m = trimesh.boolean.difference([m,well], engine='manifold')
        clr = trimesh.creation.cylinder(radius=1.15, height=6.4, sections=48)
        clr.apply_translation([sx,sy,24.2])   # 21.0..27.4 (overlaps well, exits top)
        m = trimesh.boolean.difference([m,clr], engine='manifold')

print("\nFINAL:", m.is_watertight, "parts", len(m.split(only_watertight=False)),
      "extents", np.round(m.extents,3), "volume", round(m.volume,1))
m.export('rear_v5.stl')
print("exported rear_v5.stl")
EOF