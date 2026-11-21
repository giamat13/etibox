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
LID_KL = 10.0           # lid knuckle/arm width (tangential): wider = stronger arm root
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
PLUG_Z0 = ZH - LID_T / 2 - PLUG_D            # plug bottom z (closed)
# ---- latch (replaces the old snap ring) ----
# A flexible tongue stands in the solid hub, just inside each pocket. Its lip hooks over a tab on the lid's
# hub end. The tongue stands upright, so it flexes along the printed layers (the strong direction).
# Close: the lid tab pushes the 45 deg ramp, the tongue bends toward the centre and clicks back over the tab.
# Open: push the tongue top toward the centre with a thumb, lift the lid by its grip ridge.
LATCH = float(os.environ.get("ETIBOX_LATCH", 0.5))   # lip overlap over the lid tab (holding depth)
LATCH_W = 6.0           # tongue / tab width
TONGUE_T = 1.3         # tongue thickness (3 perimeters + margin)
TONGUE_L = 9.0          # tongue free length below the body top
SLOT = 1.2              # gap behind the tongue (room to bend)
PAD_W, PAD_H = 8.0, 5.0  # release lever pad on the tongue top (width limited by the neighbour levers)
FIN_W, FIN_H, FIN_L = 12.0, 4.5, 6.0   # lift fin on each lid: pinch it between thumb and finger
TAB = 3.0              # lid tab length past the recess edge, toward the centre
XR = recess0.bounds[0]                 # recess edge (hub side), sector 0
T0 = XR - TAB                          # lid tab tip (closed)
LID_TOP = ZH + LID_T / 2
LIP_Z0 = LID_TOP + 0.05                # lip underside, 0.05 above the closed lid
LIP_H = 1.4            # thick enough for a 50 N pull at 2x safety
TONGUE_TOP = LIP_Z0 + LIP_H + LATCH    # 45 deg ramp rises LATCH+gap over the lip
TX1 = T0 - CLR                         # tongue front face
TX0 = TX1 - TONGUE_T                   # tongue back face


def latch_cuts():
    """Body cuts for sector 0: recess under the lid tab, slot behind and beside the tongue."""
    tab_seat = trimesh.creation.box([XR - TX1 + 0.5, LATCH_W + 2 * CLR, SEAT_D + 2])
    tab_seat.apply_translation([(XR + TX1 + 0.5) / 2, 0, H - SEAT_D + (SEAT_D + 2) / 2])
    slot_b = trimesh.creation.box([SLOT, LATCH_W + 2 * SLOT, TONGUE_L + 2])
    slot_b.apply_translation([TX0 - SLOT / 2, 0, H - TONGUE_L + (TONGUE_L + 2) / 2])
    sides = []
    for s in (1, -1):
        sd = trimesh.creation.box([TONGUE_T + 0.01, SLOT, TONGUE_L + 2])
        sd.apply_translation([(TX0 + TX1) / 2, s * (LATCH_W / 2 + SLOT / 2), H - TONGUE_L + (TONGUE_L + 2) / 2])
        sides.append(sd)
    return [tab_seat, slot_b] + sides


def latch_tongue_top():
    """Part of tongue + lip above the body top (sector 0). Profile in (x, z), extruded along y."""
    prof = Polygon([(TX0, H - 0.5), (TX1, H - 0.5), (TX1, LIP_Z0), (T0 + LATCH, LIP_Z0),
                    (T0 + LATCH, LIP_Z0 + 0.6), (TX1, LIP_Z0 + 0.6 + (T0 + LATCH - TX1)), (TX1, TONGUE_TOP),
                    (TX0, TONGUE_TOP)])
    m = trimesh.creation.extrude_polygon(prof, LATCH_W)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation([0, LATCH_W / 2, 0])
    # release lever: wide pad above the lip so a whole fingertip (adult / elderly) can push it.
    # Flares from LATCH_W to PAD_W at 45 deg (no unsupported overhang when printed upright).
    fl = (PAD_W - LATCH_W) / 2
    pp = Polygon([(-LATCH_W / 2, TONGUE_TOP - 0.01), (LATCH_W / 2, TONGUE_TOP - 0.01), (PAD_W / 2, TONGUE_TOP + fl),
                  (PAD_W / 2, TONGUE_TOP + PAD_H), (-PAD_W / 2, TONGUE_TOP + PAD_H), (-PAD_W / 2, TONGUE_TOP + fl)])
    pad = trimesh.creation.extrude_polygon(pp, TX1 - TX0)          # profile (y, z), extruded along x
    pad.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))   # (y,z,x)->(y,-x,z)
    pad.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 0, 1]))   # -> (x, y, z)
    pad.apply_translation([TX0 - pad.bounds[0][0], 0, 0])
    return union([m, pad])


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
    cuts += [rotz(c, a) for c in latch_cuts()]
body = diff(body, cuts)

adds = []
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
    adds.append(rotz(latch_tongue_top(), a))
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
    # latch tab under the tongue lip + grip ridge to lift the lid
    tab = trimesh.creation.box([XR + CLR - T0 + 0.5, LATCH_W, LID_T])
    tab.apply_translation([(XR + CLR + T0 + 0.5) / 2, 0, ZH])
    # lift fin: vertical face toward the centre for the thumb, 45 deg back toward the hinge
    # (that face points down in the 90 deg print pose, so it prints without support)
    xa = XR + 2.0
    fp = Polygon([(xa, LID_TOP - 0.2), (xa + FIN_L, LID_TOP - 0.2), (xa + FIN_L - FIN_H, LID_TOP + FIN_H),
                  (xa, LID_TOP + FIN_H)])
    fin = trimesh.creation.extrude_polygon(fp, FIN_W)
    fin.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    fin.apply_translation([0, FIN_W / 2, 0])
    fin = trimesh.boolean.intersection([fin, ext(plate.buffer(-0.6, 32), FIN_H + 2, ZH)], engine="manifold")
    parts += [tab, fin]
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

def clean(m):
    """Weld vertices to STL precision and drop zero-area slivers, so the saved file splits into the same
    closed parts as in memory (unwelded near-duplicates broke the body into ~170 fragments on reload)."""
    # manifold's simplify collapses edges shorter than the tolerance while keeping the mesh closed
    import manifold3d as mf
    man = mf.Manifold(mf.Mesh(vert_properties=m.vertices.astype("float32"), tri_verts=m.faces.astype("uint32")))
    out = man.simplify(1e-3).to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts, process=True)


body = clean(body)
lids = [clean(l) for l in lids]
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
