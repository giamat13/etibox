"""etibox: 6-compartment flower pill box, each compartment with its own HINGED lid
(print-in-place pin hinge). Lids print standing open at 90 deg (no bridging over the pockets);
fold them down by hand after printing. Units: mm."""
import math
import os
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
KR = 4.0                # knuckle radius (1.95 mm wall around the pin hole)
PIN_R, HOLE_R = 1.7, 2.05   # 3.4 mm pin (was 2.8), 0.35 mm print-in-place clearance
STOP_DEG = float(os.environ.get("ETIBOX_STOP", 150))  # open stop: lid leans ~60 deg past vertical, gravity keeps it open
TOOTH_R = 5.0           # stop tooth on lid knuckle hits the slot floor at STOP_DEG
NOTCH_W = 7.0          # fingernail notch at the lid's free (hub) end, to lift the lid
LID_KL = 10.0           # lid knuckle/arm width (tangential): wider = stronger arm root
GAP = 0.5               # gap lid knuckle <-> body knuckle
BK_L = 5.0              # body knuckle length each side
BEAD = float(os.environ.get("ETIBOX_BEAD", 0.55))   # snap bead protrusion beyond the lid skirt wall (skirt sits CLR inside the pocket wall)
BEAD_F = 0.3            # flat top of the bead; 45 deg ramps both sides
PLAY = 0.1              # radial play of the seated bead in its groove
SKIRT_D = 2.4           # skirt below the plug carrying the bead: keeps the groove >= 1.2 mm below the lid seat
SKIRT_T = 1.2           # skirt wall (3 perimeters)
HINGE_FREE = 6.0        # no skirt/bead/groove within this distance of pocket end near hinge


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
PLUG_Z0 = ZH - LID_T / 2 - PLUG_D            # plug bottom z (closed)
SKIRT_Z0 = PLUG_Z0 - SKIRT_D                  # skirt bottom z (closed)
BEAD_Z0 = SKIRT_Z0 + 0.1                      # bead ramp starts here
BEAD_TOP = BEAD_Z0 + 2 * BEAD + BEAD_F
GROOVE = BEAD - CLR + PLAY                    # groove depth beyond the pocket wall
_c = pocket0.centroid
_free3d = trimesh.creation.box([200, 200, 200])
_free3d.apply_translation([X_POCKET - HINGE_FREE + 100, 0, 0])


def sweep_ring(section, n=180):
    """Solid swept around the pocket outline. section: closed polygon of (e, z), e = offset from
    the pocket wall (+ = into the body wall). Offsets are sampled on rays from the pocket centroid
    (pocket is star-shaped), so every 45 deg ramp is a true slope, not a staircase."""
    import numpy as np, shapely
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    far = np.c_[_c.x + 200 * np.cos(ang), _c.y + 200 * np.sin(ang)]
    lines = shapely.linestrings([[(_c.x, _c.y), tuple(p)] for p in far])
    rings = {}
    for e, _ in section:
        if e not in rings:
            pts = shapely.intersection(lines, pocket0.buffer(e, 64).exterior)
            rings[e] = np.array([min(getattr(p, "geoms", [p]), key=lambda q: q.distance(_c)).coords[0] for p in pts])
    V = np.vstack([np.c_[rings[e], np.full(n, z)] for e, z in section])
    S = len(section)
    F = []
    for j in range(S):
        jn = (j + 1) % S
        for i in range(n):
            a, b, c, d = j * n + i, j * n + (i + 1) % n, jn * n + (i + 1) % n, jn * n + i
            F += [[a, b, c], [a, c, d]]
    m = trimesh.Trimesh(V, F, process=True)
    if m.volume < 0:
        m.invert()
    return trimesh.boolean.difference([m, _free3d], engine="manifold")


# groove = bead outline pushed out by PLAY; roof 52 deg (steeper than 45 -> prints without support)
ROOF = 1.3              # groove roof rise per mm of depth
groove_ring = sweep_ring([(-0.6, BEAD_Z0 - 0.4),
                          (GROOVE, BEAD_Z0 + BEAD),
                          (GROOVE, BEAD_Z0 + BEAD + BEAD_F),
                          (-0.6, BEAD_Z0 + BEAD + BEAD_F + (GROOVE + 0.6) * ROOF)])
# lid skirt + bead + inner fillet (fillet keeps the skirt's hub end printable when the lid prints standing)
skirt_ring = sweep_ring([(-CLR - SKIRT_T - 2.4, PLUG_Z0 + 0.3),
                         (-CLR - SKIRT_T - 2.4, PLUG_Z0),
                         (-CLR - SKIRT_T, SKIRT_Z0),
                         (-CLR, SKIRT_Z0),
                         (-CLR, BEAD_Z0),
                         (-CLR + BEAD, BEAD_Z0 + BEAD),
                         (-CLR + BEAD, BEAD_Z0 + BEAD + BEAD_F),
                         (-CLR, BEAD_TOP),
                         (-CLR, PLUG_Z0 + 0.3)])

# ---- body ----
body = ext(outline, H)
cuts = []
for i in range(N):
    a = 2 * math.pi * i / N
    cuts.append(ext(rotate(pocket0, a, origin=(0, 0), use_radians=True), H - FLOOR + 1, FLOOR))
    cuts.append(ext(rotate(recess0, a, origin=(0, 0), use_radians=True), SEAT_D + 1, H - SEAT_D))
    slot = trimesh.creation.box([12, LID_KL + 2 * GAP, 14])
    slot.apply_translation([X_POCKET + 1.6 + 6, 0, ZH - KR - 0.6 + 7])   # 1.6 mm wall pocket|slot
    cuts.append(rotz(slot, a))
    arm_clear = trimesh.creation.box([1.0, LID_KL + 2 * GAP, SEAT_D + 1])   # lid arm passes here: wall only below the seat
    arm_clear.apply_translation([X_POCKET + FLANGE + 0.5, 0, H - SEAT_D + (SEAT_D + 1) / 2])
    cuts.append(rotz(arm_clear, a))
    cuts.append(rotz(groove_ring, a))
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
notches = []
for i in range(N):
    nb = trimesh.creation.box([5.5, NOTCH_W, SEAT_D + 1.5 + 3])
    nb.apply_translation([11.5 + 5.5 / 2, 0, H - SEAT_D - 1.5 + (SEAT_D + 1.5 + 3) / 2])   # starts past the hub rim (r 11): no 0.5 mm rim sliver
    notches.append(rotz(nb, 2 * math.pi * i / N))
body = diff(body, notches)


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
    gus = trimesh.creation.box([XH - (X_POCKET - 1.5), LID_KL, KR - 0.6])   # arm gusset above plate
    gus.apply_translation([(XH + X_POCKET - 1.5) / 2, 0, ZH + (KR - 0.6) / 2])
    parts += [arm, gus, cyl_y(KR, -LID_KL / 2, LID_KL / 2, XH, ZH)]
    # leading tooth corner (half-width 1.5) reaches the floor first: compensate so contact is at STOP_DEG
    rc = math.hypot(TOOTH_R, 1.5)
    phi0 = math.radians(STOP_DEG - math.degrees(math.asin((KR + 0.6) / rc)) + math.degrees(math.atan2(1.5, TOOTH_R)))
    tooth = trimesh.creation.box([TOOTH_R, LID_KL, 3.0])
    tooth.apply_translation([TOOTH_R / 2, 0, 0])
    tooth.apply_transform(trimesh.transformations.rotation_matrix(-phi0, [0, 1, 0]))
    tooth.apply_translation([XH, 0, ZH])
    if os.environ.get("ETIBOX_TOOTH", "0") == "1":
        parts.append(tooth)
    parts.append(skirt_ring)   # snap skirt with 45 deg bead
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

white = trimesh.util.concatenate([body] + lids)
black = trimesh.util.concatenate(inlays)
if not os.environ.get("ETIBOX_NO_EXPORT"):
    os.makedirs("models", exist_ok=True)
    white.export("models/etibox_white_part.stl")      # body + lids with engraved symbols (multicolor: white filament)
    black.export("models/etibox_black_part.stl")      # symbol inlays only (multicolor: black filament)
    # single-colour version: same as white part, symbols just engraved
    white.export("models/etibox_all_white.stl")
print("body watertight", body.is_watertight, "white bounds", white.bounds.round(1).tolist(),
      "black shells", len(black.split(only_watertight=False)))
