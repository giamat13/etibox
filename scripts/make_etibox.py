"""etibox: 6-compartment flower pill box, each compartment with its own HINGED lid
(print-in-place pin hinge). Lids print standing open at 90 deg (no bridging over the pockets);
fold them down by hand after printing. Units: mm."""
import math
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

N = 6
R_LOBE, R_RING = 27.0, 36.0
H = 24.0
FLOOR = 2.4
WALL = 2.4
HUB_R = 12.0
SEAT_D = 2.4            # lid recess depth
FLANGE = 1.2            # recess wider than opening
CLR = 0.3               # lid-to-recess clearance
LID_T = 2.4
PLUG_D = 1.6
X_POCKET = 53.0         # pockets end here (radially); hinge zone beyond
XH = 59.0               # hinge axis radial position
ZH = H - 0.9            # hinge axis height (lid mid-plane)
KR = 3.4                # knuckle radius
PIN_R, HOLE_R = 1.4, 1.75
LID_KL = 8.0            # lid knuckle length (tangential)
GAP = 0.5               # gap lid knuckle <-> body knuckle
BK_L = 5.0              # body knuckle length each side


def ext(poly, h, z=0.0):
    if hasattr(poly, "geoms"):
        return trimesh.util.concatenate([ext(g, h, z) for g in poly.geoms])
    m = trimesh.creation.extrude_polygon(poly, h)
    m.apply_translation([0, 0, z])
    return m


def union(ms):
    return trimesh.boolean.union(ms, engine="manifold")


def diff(a, bs):
    return trimesh.boolean.difference([a] + bs, engine="manifold")


def cyl_y(r, y0, y1, x, z):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=48)
    c.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def rotz(m, ang):
    m = m.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
    return m


lobes = [Point(R_RING * math.cos(2 * math.pi * i / N), R_RING * math.sin(2 * math.pi * i / N)).buffer(R_LOBE, 64) for i in range(N)]
outline = unary_union(lobes + [Point(0, 0).buffer(R_RING, 64)]).buffer(-2).buffer(2)

half = math.pi / N
r_out = R_RING + R_LOBE
wedge = Polygon([(0, 0)] + [(r_out * math.cos(-half + 2 * half * k / 24), r_out * math.sin(-half + 2 * half * k / 24)) for k in range(25)])
wedge = wedge.difference(Point(0, 0).buffer(HUB_R, 64)).intersection(lobes[0].buffer(-WALL))
pocket0 = wedge.buffer(-WALL).buffer(2.0, 32).buffer(-2.0, 32).intersection(box(0, -60, X_POCKET, 60))
recess0 = pocket0.buffer(FLANGE, 32)

# ---- body ----
body = ext(outline, H)
cuts = []
for i in range(N):
    a = 2 * math.pi * i / N
    cuts.append(ext(rotate(pocket0, a, origin=(0, 0), use_radians=True), H - FLOOR + 1, FLOOR))
    cuts.append(ext(rotate(recess0, a, origin=(0, 0), use_radians=True), SEAT_D + 1, H - SEAT_D))
    slot = trimesh.creation.box([12, LID_KL + 2 * GAP, 14])
    slot.apply_translation([X_POCKET + 1.2 + 6, 0, ZH - 4.2 + 7])
    cuts.append(rotz(slot, a))
body = diff(body, cuts)

adds = [ext(Point(0, 0).buffer(HUB_R - 1).difference(Point(0, 0).buffer(HUB_R - 3)), 1.0, H)]
for i in range(N):
    a = 2 * math.pi * i / N
    for s in (1, -1):
        y0, y1 = sorted((s * (LID_KL / 2 + GAP), s * (LID_KL / 2 + GAP + BK_L)))
        k = cyl_y(KR, y0, y1, XH, ZH)
        prof = Polygon([(X_POCKET + 1.9, H - 14.5), (X_POCKET + 1.9, ZH), (XH + KR, ZH), (XH + KR, ZH - 1),
                        (XH - 1.4, ZH - 1 - (XH + KR - 44.0)), (XH - 1.4, H - 14.5)])
        col = trimesh.creation.extrude_polygon(prof, y1 - y0)   # profile in (x,y)=(x,z), extruded along z
        col.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))  # -> (x, -z, y)
        col.apply_translation([0, y1, 0])
        adds += [rotz(k, a), rotz(col, a)]
    pin = cyl_y(PIN_R, -(LID_KL / 2 + GAP + BK_L), LID_KL / 2 + GAP + BK_L, XH, ZH)
    adds.append(rotz(pin, a))
body = union([body] + adds)


# ---- lids (printed open, 90 deg) ----
CX = 28.0   # symbol centre (radial), "up" = +x


def rays(angles, r0, r1, w=0.9):
    out = []
    for a in angles:
        ray = box(CX + r0, -w / 2, CX + r1, w / 2)
        out.append(rotate(ray, a, origin=(CX, 0)))
    return unary_union(out)


def symbol(kind):
    if kind == "noon":      # full sun
        return unary_union([Point(CX, 0).buffer(3.2, 32), rays(range(0, 360, 45), 4.4, 6.8)])
    if kind == "morning":   # half sun on the horizon
        half = Point(CX, 0).buffer(3.2, 32).intersection(box(CX, -5, CX + 5, 5))
        horizon = box(CX - 1.4, -7.5, CX - 0.5, 7.5)
        return unary_union([half, horizon, rays(range(-60, 61, 30), 4.4, 6.8)])
    moon = Point(CX, 0).buffer(5.0, 48).difference(Point(CX + 1.8, 2.2).buffer(4.2, 48))   # evening crescent
    return moon


def make_lid(kind):
    plate = recess0.buffer(-CLR, 32)
    parts = [ext(plate, LID_T, ZH - LID_T / 2),
             ext(pocket0.buffer(-CLR, 32), PLUG_D, ZH - LID_T / 2 - PLUG_D)]
    arm = trimesh.creation.box([XH - (X_POCKET - 1.5), LID_KL, LID_T])
    arm.apply_translation([(XH + X_POCKET - 1.5) / 2, 0, ZH])
    parts += [arm, cyl_y(KR, -LID_KL / 2, LID_KL / 2, XH, ZH)]
    parts.append(ext(Point(X_POCKET - 8.0, 0).buffer(3.0, 32), 1.6, ZH + LID_T / 2))   # finger knob
    lid = union(parts)
    engrave = ext(symbol(kind), 1.5, ZH + LID_T / 2 - 0.8)   # 0.8 mm deep
    return diff(lid, [cyl_y(HOLE_R, -LID_KL / 2 - 1, LID_KL / 2 + 1, XH, ZH), engrave])


KINDS = ['morning', 'morning', 'noon', 'noon', 'evening', 'evening']
lid_by_kind = {k: make_lid(k) for k in set(KINDS)}
lids = []
for i in range(N):
    l = lid_by_kind[KINDS[i]].copy()
    l.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0], point=[XH, 0, ZH]))
    lids.append(rotz(l, 2 * math.pi * i / N))

def place(m, i):
    m = m.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0], point=[XH, 0, ZH]))
    return rotz(m, 2 * math.pi * i / N)


inlays = [place(ext(symbol(KINDS[i]), 0.8, ZH + LID_T / 2 - 0.8), i) for i in range(N)]

import os
os.makedirs("models", exist_ok=True)
white = trimesh.util.concatenate([body] + lids)
black = trimesh.util.concatenate(inlays)
white.export("models/etibox_white_part.stl")      # body + lids with engraved symbols (multicolor: white filament)
black.export("models/etibox_black_part.stl")      # symbol inlays only (multicolor: black filament)
# single-colour version: same as white part, symbols just engraved
white.export("models/etibox_all_white.stl")
print("body watertight", body.is_watertight, "white bounds", white.bounds.round(1).tolist(),
      "black shells", len(black.split(only_watertight=False)))
