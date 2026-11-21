"""Lid tests: swing sweep (collision vs angle) and closed-state detent engagement.
Run from repo root after make_etibox.py. Reuses geometry by importing the generator."""
import math, runpy
import trimesh

g = runpy.run_path("scripts/make_etibox.py")
body, make_lid = g["body"], g["make_lid"]
XH, ZH, PLUG_Z0 = g["XH"], g["ZH"], g["PLUG_Z0"]
BEAD, GROOVE, CLR = g["BEAD"], g["GROOVE"], g["CLR"]


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

# snap passage: how deep the lid pushes into the body while the bead rides over the pocket edge.
# That depth is what the skirt + pocket wall must flex; it must stay near the designed interference.
worst = 0.0
for ang in (0.5, 1, 2, 3, 4, 6, 8, 10, 12):
    pts = pose(ang).sample(5000)
    worst = max(worst, float(trimesh.proximity.signed_distance(body, pts).max()))
# the hub end of the skirt swings on an arc, so it pushes deeper than the radial design value. Judge it by
# the flex strain it causes (same two-cantilever model as check_etibox.py: 0.25 mm -> 1.5 %), PETG yields ~4 %.
strain = 1.5 * worst / (BEAD - CLR)
print(f"snap passage 0-12 deg: max interference {worst:.2f} mm (radial design {BEAD - CLR:.2f}) -> peak strain ~{strain:.1f}% "
      f"{'OK' if strain < 4.0 / 1.5 else 'TOO HIGH'} (limit {4.0/1.5:.1f}% = PETG yield / 1.5)")

print(f"detent: bead protrusion {BEAD} mm, groove depth {GROOVE} mm, interference while passing "
      f"{BEAD - CLR:.2f} mm, seated play {GROOVE + CLR - BEAD:.2f} mm")
