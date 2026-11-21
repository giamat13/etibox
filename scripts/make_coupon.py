"""Detent calibration plate: one compartment + lid printed 4x with bead 0.45/0.55/0.65/0.75 mm.
Print it first on the P1S, flip/shake each, keep the value that clicks firmly but opens with one finger.
Run from repo root: python scripts/make_coupon.py"""
import math, os, runpy
import trimesh
from shapely.geometry import Polygon
from shapely.affinity import translate

os.environ["ETIBOX_NO_EXPORT"] = "1"
BEADS = [0.3, 0.5, 0.7, 0.9]   # latch lip overlap, mm
parts = []
for n, b in enumerate(BEADS):
    os.environ["ETIBOX_LATCH"] = str(b)
    g = runpy.run_path("scripts/make_etibox.py")
    r, h = 72.0, math.pi / 6
    wedge = Polygon([(0, 0)] + [(r * math.cos(-h + 2 * h * k / 20), r * math.sin(-h + 2 * h * k / 20)) for k in range(21)])
    cut = trimesh.creation.extrude_polygon(wedge, 80)
    piece = trimesh.boolean.intersection([g["body"], cut], engine="manifold")
    piece = trimesh.util.concatenate([piece, g["lids"][0]])
    piece.apply_translation([(n % 2) * 78 - 40, (n // 2) * 72 - 36, 0])
    parts.append(piece)
plate = trimesh.util.concatenate(parts)
plate.export("models/etibox_detent_coupon.stl")
print("coupon bounds", plate.bounds.round(1).tolist())
