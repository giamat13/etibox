"""Geometric / physics checks for etibox.stl against a Bambu Lab P1S (256x256x256 mm bed, 0.4 nozzle)."""
import numpy as np
import trimesh

m = trimesh.load("models/etibox.stl")
parts = m.split(only_watertight=False)
ok = True
def rep(name, good, detail):
    global ok
    ok &= bool(good)
    print(("PASS " if good else "FAIL ") + name + ": " + detail)

ext = m.extents
rep("fits P1S bed (256x256x256)", all(ext < [256, 256, 256]), f"{ext.round(1).tolist()} mm")
rep("watertight shells", all(p.is_watertight for p in parts), f"{len(parts)} shells, {sum(p.is_watertight for p in parts)} watertight")
rep("positive volume", m.volume > 0, f"{m.volume/1000:.1f} cm3")

# minimum wall thickness: ray cast inward from face centres of body
body = max(parts, key=lambda p: p.volume)
idx = np.random.default_rng(0).choice(len(body.faces), 4000, replace=False)
c = body.triangles_center[idx]; n = body.face_normals[idx]
hits = body.ray.intersects_location(c - n * 1e-3, -n, multiple_hits=False)
loc, ray_i, _ = hits
d = np.linalg.norm(loc - c[ray_i], axis=1)
d = d[d > 0.05]
wall_min = np.percentile(d, 1)
rep("wall >= 1.2 mm (3 perimeters at 0.4)", wall_min >= 1.2, f"1st percentile thickness {wall_min:.2f} mm")

# overhang: faces pointing down steeper than 45 deg from vertical
down = body.face_normals[:, 2] < -np.cos(np.radians(45))
low = body.triangles_center[:, 2] < 0.05
bad = down & ~low
area = body.area_faces[bad].sum()
rep("overhangs > 45deg (support-free)", area < 5, f"{area:.1f} mm2 of unsupported overhang")

# strength: wall bending as a cantilever (PETG E~2000 MPa, yield~40 MPa), 5 N finger load at rim
t = max(wall_min, 1.2); L = 22.0; w = 10.0; F = 5.0
sigma = 6 * F * L / (w * t * t)
rep("wall stress under 5 N poke < 40 MPa/3", sigma < 40/3, f"{sigma:.1f} MPa (safety factor {40/sigma:.1f}x)")
print("ALL PASS" if ok else "SOME CHECKS FAILED")
