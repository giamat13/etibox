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
for ang in (0, 5, 10, 15, 20, 30, 45, 60, 90):
    m = lid.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-ang), [0, 1, 0], point=[XH, 0, ZH]))
    print(f"{ang:5d}  {vol(body, m):10.2f}")

print(f"detent: bead protrusion {BEAD} mm, groove depth {GROOVE} mm, interference while passing "
      f"{BEAD - CLR:.2f} mm, seated play {GROOVE + CLR - BEAD:.2f} mm")
# holding force estimate (PETG E~1.3 GPa, wall 2.4 mm, bead length ~60 mm): cantilever stiffness crude
E, t, L = 1300.0, 2.4, 60.0     # MPa, mm, mm
d = BEAD - CLR
k = E * L * t ** 3 / (4 * 10.0 ** 3)          # N/mm, 10 mm effective span, crude
N_press = k * d
F_hold = N_press * 0.5 * 2.0                  # 45deg-ish lead flank: tan ~ 1 minus friction
print(f"rough pull-open resistance ~{F_hold:.0f} N vs lid+6 pills weight ~0.1 N (shake 10 g: ~1 N)")
