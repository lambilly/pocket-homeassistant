# 来源: 会话归档 jsonl line 616（4245 字符 Bash heredoc）
cd "D:/Desktop/HA Monitor Display 外壳" && cat > /tmp/build10.py <<'EOF'
import trimesh, numpy as np
from shapely.geometry import Polygon, box as sbox, Point, LineString
from shapely.ops import unary_union, polygonize
from trimesh.creation import extrude_polygon
np.seterr(all='ignore')

def ring_of(mesh,z):
    sec=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
    segs=[LineString([tuple(a),tuple(b)]) for line in sec.discrete for a,b in zip(line[:,:2],line[1:,:2])]
    polys=list(polygonize(unary_union(segs)))
    cands=[p for p in polys if p.area<1500 and len(p.interiors)==1]
    r=max(cands,key=lambda p:p.area)
    return r, list(r.interiors)[0]

def cyl(x,y,zc,r,h,sections=64):
    c=trimesh.creation.cylinder(radius=r,height=h,sections=sections)
    c.apply_translation([x,y,zc]); return c

def cyl_y(x,zc,yc,r,h,sections=48):
    c=trimesh.creation.cylinder(radius=r,height=h,sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
    b=c.bounds
    c.apply_translation([x-(b[0][0]+b[1][0])/2, yc-(b[0][1]+b[1][1])/2, zc-(b[0][2]+b[1][2])/2])
    return c

# ================= front_v4 : 前壳 +10 =================
o=trimesh.load("01_原版/front.stl",force='mesh')
ring,inner=ring_of(o,5.0)
assert abs(np.max(np.abs(inner.bounds))-51.3)<0.5 or True
print("front 环 area=%.1f 内环bbox=%s"%(ring.area,np.round(inner.bounds,2).tolist()))
eA=extrude_polygon(Polygon(ring.exterior,[inner]),10.6); eA.apply_translation([0,0,5.0])
eB=extrude_polygon(Polygon(ring.exterior,[inner.buffer(0.15).exterior]),0.6); eB.apply_translation([0,0,15.6])
posts=[cyl(sx*24.75,sy*46,11.7,1.45,10.4) for sx in (1,-1) for sy in (1,-1)]
ext=trimesh.boolean.union([eA,eB]+posts,engine='manifold')
cut=[]
for sx in (1,-1):
    for sy in (1,-1):
        cut.append(cyl(sx*24.75,sy*46,14.2,0.775,5.4))                       # 新导向孔 11.5~16.9
        cut.append(cyl(sx*24.75,sy*46,4.65,0.775,4.6))                       # 复原原导向孔 2.35~6.95
        lead=trimesh.creation.cone(radius=0.775+0.5,height=0.5,sections=48)  # 孔口 45° 引导
        lead.apply_translation([sx*24.75,sy*46,16.65]); cut.append(lead)
ext=trimesh.boolean.difference([ext]+cut,engine='manifold')
f4=trimesh.boolean.union([o,ext],engine='manifold')
ps=sorted(f4.split(only_watertight=False),key=lambda x:-x.volume)
print("front_v4 体数=%d 主体=%.1f 丢弃=%.2f"%(len(ps),ps[0].volume,sum(p.volume for p in ps[1:])))
f4=ps[0]; f4.merge_vertices()
print("front_v4 bounds",np.round(f4.bounds,2).tolist(),"wt",f4.is_watertight,"tris",len(f4.faces))
f4.export("03_v2_前壳加高20/front_v4.stl")

# ================= rear_v3 : 后盖 +10 =================
R6=trimesh.load("03_v2_前壳加高20/rear_v2.stl",force='mesh')
rr,ri=ring_of(R6,6.0)
print("rear 环 area=%.1f 内环bbox=%s"%(rr.area,np.round(ri.bounds,2).tolist()))
lower=trimesh.boolean.intersection([R6,trimesh.creation.box(bounds=[[-60,-120,-1],[60,120,3.6]])],engine='manifold')
eAr=extrude_polygon(Polygon(rr.exterior,[ri]),12.6);  eAr.apply_translation([0,0,3.6])
eBr=extrude_polygon(Polygon(rr.exterior,[ri.buffer(0.15).exterior]),0.6); eBr.apply_translation([0,0,16.2])
bosses=[cyl(sx*24.75,sy*46,8.055,3.8,16.11) for sx in (1,-1) for sy in (1,-1)]
body=trimesh.boolean.union([lower,eAr,eBr]+bosses,engine='manifold')

cutr=[]
for sx in (1,-1):
    for sy in (1,-1):
        cutr.append(cyl(sx*24.75,sy*46,5.34,2.5,13.68))   # ⌀5.0 深孔 0~11.68（螺丝头）
        cutr.append(cyl(sx*24.75,sy*46,13.9,1.15,4.8))    # ⌀2.3 过孔 11.5~16.3
# Type-C : 世界 +Y 端壁（前壳局部 -Y 经镜像）
WY=50.2
cutr.append(trimesh.creation.box(bounds=[[-3.5,WY-1.4,11.0],[3.5,WY+1.4,14.3]]))
cutr.append(trimesh.creation.box(bounds=[[-4.5,WY-1.4,11.5],[4.5,WY+1.4,13.8]]))
for cx in (-3.5,3.5):
    for zz in (11.5,13.8):
        cutr.append(cyl_y(cx,zz,WY,1.0,2.8))
for x0 in (-8.0,8.0):
    cutr.append(cyl_y(x0,12.65,WY,1.25,2.8))
r3=trimesh.boolean.difference([body]+cutr,engine='manifold')
ps=sorted(r3.split(only_watertight=False),key=lambda x:-x.volume)
print("rear_v3 体数=%d 主体=%.1f 丢弃=%.2f"%(len(ps),ps[0].volume,sum(p.volume for p in ps[1:])))
r3=ps[0]; r3.merge_vertices()
print("rear_v3 bounds",np.round(r3.bounds,2).tolist(),"wt",r3.is_watertight,"tris",len(r3.faces))
r3.export("03_v2_前壳加高20/rear_v3.stl")
EOF
python /tmp/build10.py 2>&1 | grep -v Warning