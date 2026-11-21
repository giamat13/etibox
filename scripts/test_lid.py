"""Lid tests: swing sweep (collision vs angle) and closed-state detent engagement.
Run from repo root after make_etibox.py. Reuses geometry by importing the generator."""
import math, runpy
import trimesh

g = runpy.run_path("scripts/make_etibox.py")
body, make_lid = g["body"], g["make_lid"]
XH, ZH, PLUG_Z0 = g["XH"], g["ZH"], g["PLUG_Z0"]



def vol(a, b):
    try:
        i = trimesh.boolean.intersection([a, b], engine="manifold")
        return float(i.volume) if len(i.vertices) else 0.0
    except Exception:
        return 0.0


# lid as modelled = CLOSED pose (flat). Rotate about hinge axis (y) to sweep.
lid = make_lid("noon")
print("angle  overlap_mm3  (0=closed, 90=open)")
def pose(ang):
    m = lid.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 1, 0], point=[XH, 0, ZH]))
    return m


stop = None
for ang in list(range(0, 100, 10)) + list(range(100, int(__import__('os').environ.get('SWEEP_MAX', 210)), 2)):
    v = vol(body, pose(ang))
    print(f"{ang:5d}  {v:10.2f}")
    if stop is None and ang > 30 and v > 0.05:
        stop = ang
print(f"OPEN STOP at ~{stop} deg (first contact)")

# print-in-place clearance in the printed pose (90 deg): lid surface must stay >= 0.3 mm from body
import numpy as np
m = pose(90)
pts = m.sample(20000)
d = np.abs(trimesh.proximity.signed_distance(body, pts))
print(f"print pose 90 deg: min lid-body clearance {d.min():.2f} mm (need >= 0.30)")

print(f"latch: lip overlap {g['LATCH']} mm over the lid tab, tongue {g['TONGUE_T']} x {g['TONGUE_L']} mm")
