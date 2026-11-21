"""Print / strength checks for etibox against a Bambu Lab P1S (256x256x256 mm bed, 0.4 nozzle), PETG.
Run from repo root: python scripts/check_etibox.py"""
import math, os, runpy
import numpy as np
import trimesh

os.environ["ETIBOX_NO_EXPORT"] = "1"
g = runpy.run_path("scripts/make_etibox.py")
m = trimesh.load("models/etibox_all_white.stl", force="mesh")
parts = m.split(only_watertight=False)
ok = True
def rep(name, good, detail):
    global ok
    ok &= bool(good)
    print(("PASS " if good else "FAIL ") + name + ": " + detail)

E, YIELD, STRAIN_Y = 2000.0, 40.0, 0.04          # PETG: modulus MPa, yield MPa, yield strain
ext = m.extents
rep("fits P1S bed (256x256x256)", all(ext < [256, 256, 256]), f"{ext.round(1).tolist()} mm")
rep("watertight shells", all(p.is_watertight for p in parts), f"{len(parts)} shells, {sum(p.is_watertight for p in parts)} watertight")
rep("positive volume", m.volume > 0, f"{m.volume/1000:.1f} cm3")

body = max(parts, key=lambda p: p.volume)
lids = [p for p in parts if p is not body]
c, n, a = body.triangles_center, body.face_normals, body.area_faces

# wall thickness at every face: ray straight through the material to the opposite face. A wall is two
# roughly opposed faces; a ray leaving through a face at ~90 deg is an outer corner edge, not a thin wall.
d = np.full(len(c), np.inf); opp = np.zeros(len(c), bool)
for s in range(0, len(c), 1500):   # in chunks: one big ray batch needs several GB of RAM
    k = np.arange(s, min(s + 1500, len(c)))
    loc, ri, ti = body.ray.intersects_location(c[k] - n[k] * 1e-3, -n[k], multiple_hits=False)
    ri = k[ri]
    d[ri] = np.linalg.norm(loc - c[ri], axis=1); opp[ri] = (n[ri] * n[ti]).sum(1) < -0.5
thin = (d > 0.05) & (d < 1.2) & opp
edge = (d > 0.05) & (d < 1.2) & ~opp
w = np.isfinite(d) & opp
rep("no wall thinner than 1.2 mm (3 perimeters)", a[thin].sum() < 1,
    f"{a[thin].sum():.1f} mm2 of wall under 1.2 mm; area-weighted 1st percentile {np.percentile(np.repeat(d[w], np.ceil(a[w] * 10).astype(int)), 1):.2f} mm"
    f" ({a[edge].sum():.1f} mm2 at outer corner edges, not walls)")

# overhangs (> 45 deg from vertical), body prints upright. The hinge pin is a deliberate bridge between
# the two body knuckles (print-in-place); it is reported, not failed, if its span is bridgeable.
down = n[:, 2] < -math.cos(math.radians(45))
low = c[:, 2] < 0.05
XH, ZH, PIN_R, span = g["XH"], g["ZH"], g["PIN_R"], g["LID_KL"] + 2 * g["GAP"]
ang = np.arctan2(c[:, 1], c[:, 0]); sec = np.round(ang / (2 * math.pi / g["N"])) * (2 * math.pi / g["N"])
xr = c[:, 0] * np.cos(sec) + c[:, 1] * np.sin(sec); yr = -c[:, 0] * np.sin(sec) + c[:, 1] * np.cos(sec)
pin = (np.hypot(xr - XH, c[:, 2] - ZH) < PIN_R + 0.05) & (np.abs(yr) < span / 2 + 0.05)
bad = down & ~low & ~pin
rep("overhangs > 45deg need no support", a[bad].sum() < 5, f"{a[bad].sum():.1f} mm2 unsupported")
rep("hinge pin bridge span <= 20 mm (P1S bridges PETG)", span <= 20, f"{span:.1f} mm, {a[down & pin].sum():.0f} mm2 bridged")

# lid snap: 0.25 mm interference shared by the lid skirt and the pocket wall (two cantilevers in series)
interf = g["BEAD"] - g["CLR"]
t_s, L_s = g["SKIRT_T"], g["SKIRT_D"] + g["PLUG_D"] / 2
t_w, L_w = 2 * g["WALL"], g["BEAD_Z0"] + g["BEAD"] - g["FLOOR"]
k_s, k_w = E * t_s**3 / (4 * L_s**3), E * t_w**3 / (4 * L_w**3)       # N/mm per mm width
dx_s = interf * k_w / (k_s + k_w); dx_w = interf - dx_s
eps = max(1.5 * t_s * dx_s / L_s**2, 1.5 * t_w * dx_w / L_w**2)
rep("snap strain < PETG yield strain / 2", eps < STRAIN_Y / 2,
    f"skirt {dx_s:.2f} mm + wall {dx_w:.2f} mm deflection, peak strain {eps*100:.1f}% (yield ~4%)")
gap_lip = (g["H"] - g["SEAT_D"]) - (g["BEAD_Z0"] + g["BEAD"] + g["BEAD_F"] + g["GROOVE"] * g["ROOF"])   # groove roof at the wall face
rep("material above snap groove >= 1.2 mm", gap_lip >= 1.2, f"{gap_lip:.2f} mm")

# pocket wall at the rim (outer wall minus the lid seat), 5 N finger poke at the rim, 10 mm wide strip
t_rim = 2 * g["WALL"] - g["FLANGE"]
sigma = 6 * 5.0 * g["H"] / (10 * t_rim**2)
rep("rim wall under 5 N poke < yield/3", sigma < YIELD / 3, f"wall {t_rim:.1f} mm, {sigma:.1f} MPa (safety {YIELD/sigma:.1f}x)")

# hinge pin: 20 N pull on the lid, pin simply supported over the slot
M = 20.0 * span / 4; s_pin = M / (math.pi * (2 * PIN_R)**3 / 32)
rep("hinge pin at 20 N lid pull < yield/2", s_pin < YIELD / 2, f"{s_pin:.1f} MPa (safety {YIELD/s_pin:.1f}x)")
kw = g["KR"] - g["HOLE_R"]
rep("lid knuckle wall >= 1.6 mm (4 perimeters)", kw >= 1.6, f"{kw:.2f} mm")
# lid arm root: 20 N at the lid's far end levered through the arm (LID_KL wide, LID_T + gusset thick)
t_arm = g["LID_T"] / 2 + g["KR"] - 0.6 + g["LID_T"] / 2
s_arm = 6 * 20.0 * (g["XH"] - g["X_POCKET"]) / (g["LID_KL"] * t_arm**2)
rep("lid arm root at 20 N < yield/2", s_arm < YIELD / 2, f"{s_arm:.1f} MPa (safety {YIELD/s_arm:.1f}x)")
print("ALL PASS" if ok else "SOME CHECKS FAILED")
