# 来源: 会话归档 jsonl line 405（4066 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from trimesh.transformations import rotation_matrix

f = trimesh.load('front.stl')
print("front in:", f.is_watertight, np.round(f.extents,3))

def ring(mesh, z):
    sec = mesh.section(plane_origin=[0,0,z], plane_normal=[0,0,1])
    loops=[d[:,:2] for d in sec.discrete if np.allclose(d[0],d[-1])]
    loops.sort(key=lambda l: Polygon(l).area, reverse=True)
    return orient(Polygon(loops[0], [loops[1]]).buffer(0))

rA = ring(f, 5.0)    # inner 28.05 (main cavity)
rB = ring(f, 6.0)    # inner 28.20 (0.6 lead-in chamfer zone)
print("ringA bounds", np.round(rA.bounds,2).tolist(), "area", round(rA.area,1))
print("ringB bounds", np.round(rB.bounds,2).tolist(), "area", round(rB.area,1))

# ---- 1) skirt +20mm : 5.0->25.6 (inner 28.05), 25.6->26.2 (inner 28.2) ----
eA = trimesh.creation.extrude_polygon(rA, height=25.6-5.0); eA.apply_translation([0,0,5.0])
eB = trimesh.creation.extrude_polygon(rB, height=26.2-25.6); eB.apply_translation([0,0,25.6])
f = trimesh.boolean.union([f,eA,eB], engine='manifold')
print("skirt +20:", f.is_watertight, np.round(f.extents,3), "parts", len(f.split(only_watertight=False)))

# ---- 2) 4 corner posts extended to local 26.9 (world 6.1) + new pilot ----
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        rod = trimesh.creation.cylinder(radius=1.455, height=26.9-2.2, sections=48)
        rod.apply_translation([sx,sy,2.2+(26.9-2.2)/2])
        f = trimesh.boolean.union([f,rod], engine='manifold')
        bore = trimesh.creation.cylinder(radius=0.775, height=6.0, sections=32)
        bore.apply_translation([sx,sy,22.35+3.0])     # 22.35..28.35 -> 4.55 deep from tip
        f = trimesh.boolean.difference([f,bore], engine='manifold')
print("posts +20:", f.is_watertight, "parts", len(f.split(only_watertight=False)))

# ---- 3) gussets: post -> both adjacent walls, z 5.0..26.2 ----
G=[]
for sx in (-24.75,24.75):
    for sy in (-46.0,46.0):
        ax = 1 if sx>0 else -1
        ay = 1 if sy>0 else -1
        x0,x1 = (26.1,28.06) if ax>0 else (-28.06,-26.1)
        G.append(trimesh.creation.box(bounds=[[x0,sy-0.6,5.0],[x1,sy+0.6,26.2]]))
        y0,y1 = (47.35,49.30) if ay>0 else (-49.30,-47.35)
        G.append(trimesh.creation.box(bounds=[[sx-0.6,y0,5.0],[sx+0.6,y1,26.2]]))
# mid-span wall ribs (skip -Y side: Type-C there)
G.append(trimesh.creation.box(bounds=[[24.5,-0.6,5.0],[28.06,0.6,26.2]]))
G.append(trimesh.creation.box(bounds=[[-28.06,-0.6,5.0],[-24.5,0.6,26.2]]))
G.append(trimesh.creation.box(bounds=[[-0.6,45.3,5.0],[0.6,49.30,26.2]]))
f = trimesh.boolean.union([f]+G, engine='manifold')
print("ribs:", f.is_watertight, "parts", len(f.split(only_watertight=False)))

# ---- 4) Type-C on local -Y edge: world z 11.0~14.3 -> local 18.7~22.0 ----
W,H,R,ZC = 9.0,3.3,1.0, 20.35
x0,x1,z0,z1 = -W/2, W/2, -H/2, H/2
rr = unary_union([sbox(x0+R,z0,x1-R,z1), sbox(x0,z0+R,x1,z1-R)]
   + [Point(cx,cz).buffer(R,resolution=32) for cx in (x0+R,x1-R) for cz in (z0+R,z1-R)]).buffer(0)
pr = trimesh.creation.extrude_polygon(orient(rr), height=3.6)
pr.apply_transform(rotation_matrix(np.pi/2,[1,0,0]))
pr.apply_translation([0,-48.9,ZC])
print("typec prism bounds:", np.round(pr.bounds,3).tolist(), "(want x±4.5, y -52.5~-48.9, z 18.7~22.0)")
assert np.allclose(pr.bounds,[[-4.5,-52.5,18.7],[4.5,-48.9,22.0]],atol=0.02)
f = trimesh.boolean.difference([f,pr], engine='manifold')
for sx in (-8.0,8.0):
    cyl = trimesh.creation.cylinder(radius=1.25, height=3.6, sections=48)
    cyl.apply_transform(rotation_matrix(np.pi/2,[1,0,0]))
    cyl.apply_translation([sx,-50.7,ZC])
    f = trimesh.boolean.difference([f,cyl], engine='manifold')
print("typec:", f.is_watertight, "parts", len(f.split(only_watertight=False)))

print("\nFINAL front_v2:", f.is_watertight, "extents", np.round(f.extents,3), "volume", round(f.volume,1))
f.export('front_v2.stl')
print("exported front_v2.stl")
EOF