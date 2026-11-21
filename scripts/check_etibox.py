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
# the latch lip is a deliberate wedge (thin at its tip); its strength has its own check below
rr = np.hypot(c[:, 0], c[:, 1])
thin &= ~((rr < 11.5) & (c[:, 2] > 24.2) & (c[:, 2] < 26.5))
edge = (d > 0.05) & (d < 1.2) & ~opp
w = np.isfinite(d) & opp
if a[thin].sum() >= 1:   # where (sector 0 frame: r, z, thickness) so the cause can be found
    r = np.hypot(c[thin, 0], c[thin, 1])
    for i in np.argsort(-a[thin])[:8]:
        print(f"   thin at r={r[i]:.1f} z={c[thin][i, 2]:.1f} t={d[thin][i]:.2f} area={a[thin][i]:.1f}")
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
lip = (np.abs(c[:, 2] - g['LIP_Z0']) < 0.05) & (xr > g['TX1'] - 0.05) & (xr < g['T0'] + g['LATCH'] + 0.05)
bad = down & ~low & ~pin & ~lip
rep("overhangs > 45deg need no support", a[bad].sum() < 5, f"{a[bad].sum():.1f} mm2 unsupported")
rep("latch lip overhang <= 1 mm deep (prints unsupported)", g["LATCH"] + g["CLR"] <= 1.0, f"{g['LATCH'] + g['CLR']:.1f} mm deep, {a[down & lip].sum():.0f} mm2")
rep("hinge pin bridge span <= 20 mm (P1S bridges PETG)", span <= 20, f"{span:.1f} mm, {a[down & pin].sum():.0f} mm2 bridged")

# latch tongue: upright cantilever, flexes in the layer plane. Closing bends it by LATCH + 0.05;
# releasing with a thumb bends it ~0.3 mm further.
L_t = g["TONGUE_L"] + (g["LIP_Z0"] - g["H"])
d_close, d_open = g["LATCH"] + 0.05, g["LATCH"] + 0.3
eps = 1.5 * g["TONGUE_T"] * d_open / L_t**2
rep("latch tongue strain < PETG yield strain / 2", eps < STRAIN_Y / 2,
    f"tongue {g['TONGUE_T']} x {L_t:.1f} mm, bend {d_open:.2f} mm to open, peak strain {eps*100:.1f}% (yield ~4%)")
rep("tongue can bend far enough (slot behind it)", g["SLOT"] >= d_open + 0.3, f"slot {g['SLOT']} mm, needs {d_open:.2f} mm")
k = E * g["LATCH_W"] * g["TONGUE_T"]**3 / (4 * L_t**3)
F_close = k * d_close * 2          # 45 deg ramp: push force ~ 2x the bending force (with friction)
rep("click-shut force 2-10 N (one finger)", 2 <= F_close <= 10, f"{F_close:.1f} N")
# holding: the lid tab pushes straight up on the flat lip underside -> lip shear, lip root bending
s_lip = 6 * 50.0 * g["LATCH"] / (g["LATCH_W"] * g["LIP_H"]**2)
rep("lip holds a 50 N lid pull (drop needs ~20 N) < yield/2", s_lip < YIELD / 2, f"{s_lip:.1f} MPa (safety {YIELD/s_lip:.1f}x)")
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
