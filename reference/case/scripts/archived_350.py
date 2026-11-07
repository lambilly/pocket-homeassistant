# 来源: 会话归档 jsonl line 350（3226 字符 Bash heredoc）
cd "/d/Desktop/HA Monitor Display 外壳" && python - <<'EOF'
import trimesh, numpy as np
m = trimesh.load('rear_v5.stl')
cx, cy = 24.75, 46.0

def first_from_below(r):
    l,_,_=m.ray.intersects_location(np.array([[cx+r,cy,-10.]]),np.array([[0,0,1.]]),multiple_hits=False)
    return round(l[0][2],2) if len(l) else None
def first_from_above(r):
    l,_,_=m.ray.intersects_location(np.array([[cx+r,cy,40.]]),np.array([[0,0,-1.]]),multiple_hits=False)
    return round(l[0][2],2) if len(l) else None

print("=== corner screw path (axis at 24.75,46) ===")
print(" r    from_below(expect)   from_above(expect)")
for r,eb,ea in [(0.0,'through(None)','through(None)'),(0.8,'None','None'),
                (1.5,'21.5(头位肩面)','26.8(柱顶)'),(2.0,'21.5','26.8'),
                (2.25,'21.5(⌀4.5头可过)','26.8'),(2.4,'0.0(孔外)','26.8'),(3.0,'0.0','26.8')]:
    print(f" {r:4.2f}  {str(first_from_below(r)):>8} ({eb})   {str(first_from_above(r)):>8} ({ea})")

print("\n=== screw shank path clearance D2.3 check (horizontal ray through column) ===")
for z in [10.0, 15.0, 20.0, 23.0, 25.0]:
    o=np.array([[cx-10.0,cy,z]]); d=np.array([[1,0,0.]])
    l,_,_=m.ray.intersects_location(o,d,multiple_hits=True)
    xs=sorted(round(v[0]-cx,2) for v in l)
    print(f"  z={z:5.1f}: material x-offsets {xs}  (expect hole open in ±1.15)")

print("\n=== simulated screw fit: head cylinder D4.5x1.7 from bottom to 21.5 ===")
# sample ring of points at head radius 2.25 at several heights inside well
ok=True
for z in [0.5, 5, 10, 15, 20, 21.0]:
    for ang in np.arange(0, 2*np.pi, np.pi/8):
        x,y = cx+2.25*np.cos(ang), cy+2.25*np.sin(ang)
        l,_,_=m.ray.intersects_location(np.array([[x,y,z]]),np.array([[0,0,-1.]]),multiple_hits=True)
        l2,_,_=m.ray.intersects_location(np.array([[x,y,z]]),np.array([[0,0,1.]]),multiple_hits=True)
        inside = (len(l)==0 and len(l2)==0) or (len(l)==0 and len(l2) and l2[0][2]>21.5) or (len(l2)==0 and len(l) and l[-1][2]<z)
        # simpler: point-in-mesh test
        contains = m.contains([x,y,z])
        if contains: ok=False; print(f"  BLOCKED at z={z} ang={ang:.2f}")
print("  head path clear:", ok)

print("\n=== tip reach check: tip at z=31.0 must be above column top(26.8) into front pilot zone ===")
print("  column top:", first_from_above(1.5), "-> screw engages 26.8~31.0 = 4.2mm of front pilot(26.8~31.35)")

print("\n=== other features intact ===")
def ry(x,y):
    l,_,_=m.ray.intersects_location(np.array([[x,y,40.]]),np.array([[0,0,-1.]]),multiple_hits=False)
    return round(l[0][2],2) if len(l) else None
print("  rim top:", ry(0,-51), ry(0,51), ry(29.5,0), ry(-29.5,0), "(expect 26.8)")
def rh(x,y,z):
    l,_,_=m.ray.intersects_location(np.array([[x,y,z]]),np.array([[0,1,0.]]),multiple_hits=False)
    return 'OPEN' if not len(l) else 'MAT'
print("  Type-C open z5.7~8.6:", rh(0,48,5.7), rh(0,48,7.15), rh(0,48,8.6), "| closed:", rh(0,48,5.3), rh(0,48,9.0))
print("  D2.5 holes:", rh(-8,48,7.15), rh(8,48,7.15))
print("  rib grid:", ry(-12,-20), ry(-24,-20), ry(6,-20), "(3.5/2.5)")
print("  bottom flat:", end=' ')
l,_,_=m.ray.intersects_location(np.array([[0,0,-10.]]),np.array([[0,0,1.]]),multiple_hits=False)
print(round(l[0][2],2) if len(l) else None, "(expect 0)")
EOF