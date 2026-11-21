"""Blender (Bullet) rigid-body tests for the etibox lid.
Run headless from repo root:
  blender -b --factory-startup --python scripts/sim_blender.py -- [--render]
Setup: body (animated/kinematic, or free for the drop), one lid on a hinge, 20 pills (10 g) in its pocket.
Snap detent = breakable constraint on the hinge rotation only; it breaks when the opening torque exceeds
F_hold * bead lever. F_hold = 0 reproduces the old design (no lock).
Hinge has no friction (worst case). Upper hinge limit = geometric open stop from test_lid.py."""
import bpy, json, math, sys, os
from mathutils import Matrix, Quaternion, Vector

ROOT = os.getcwd()
CFG = json.load(open(os.path.join(ROOT, "models/sim/sim.json")))
S = 0.001                                    # mm -> m
FPS, SUB = 100, 10                           # 1000 Hz physics
OPEN_STOP = float(os.environ.get("ETIBOX_OPEN_STOP", 196))   # from test_lid.py (lid rests against the outside of the box)
RENDER = "--render" in sys.argv
OPEN_F = float(os.environ.get("ETIBOX_OPEN_F", 20))   # detent used in the finger-open test
VIDEO = int(os.environ.get("ETIBOX_VIDEO", 0))   # render every Nth frame (for make_video.py)
ONLY = [k for k in os.environ.get("ETIBOX_ONLY", "").split(",") if k]
TRACE = bool(os.environ.get("ETIBOX_TRACE"))


def want(k):
    return not ONLY or k in ONLY
HX, HY, HZ = [c * S for c in CFG["hinge"]]
BEAD_LEVER = CFG["bead_r_mm"] * S


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.gravity = (0, 0, -9.81)
    bpy.ops.rigidbody.world_add()
    w = sc.rigidbody_world
    w.substeps_per_frame = SUB
    w.solver_iterations = 60
    w.use_split_impulse = True
    return sc


def imp(path, name):
    bpy.ops.wm.stl_import(filepath=os.path.join(ROOT, path), global_scale=S)
    o = bpy.context.selected_objects[0]
    o.name = name
    # importer leaves scale 0.001 on the object; Bullet then never rotates constrained bodies -> bake it in
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.select_set(False)
    return o


def rb(o, typ="ACTIVE", shape="CONVEX_HULL", mass=0.01, kin=False):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.rigidbody.object_add()
    r = o.rigid_body
    r.type, r.collision_shape, r.mass, r.kinematic = typ, shape, mass, kin
    r.use_margin, r.collision_margin = True, 0.0003
    r.friction, r.restitution = 0.5, 0.2
    r.linear_damping = r.angular_damping = 0.02
    r.collision_collections = [i in (0, 1) for i in range(20)]
    o.select_set(False)
    return r


def constraint(name, a, b, kind, breaking=None, start=0.0):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = (HX, HY, HZ)
    # orientation must be set (and the matrix updated) BEFORE the constraint reads it
    e.rotation_euler = (-math.pi / 2, 0, 0) if kind == "hinge" else (0, 0, math.pi / 2)
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = e
    bpy.ops.rigidbody.constraint_add()
    c = e.rigid_body_constraint
    c.object1, c.object2 = a, b
    c.disable_collisions = True
    # Bullet 6-DOF Y limits are capped at +-90 deg, so never use Y as the hinge axis.
    if kind == "hinge":                        # HINGE turns about the empty's local Z -> align it with world +Y
        c.type = "HINGE"
        c.use_limit_ang_z = True
        # zero = pose at sim start; opening = +world Y (same sense as Matrix.Rotation(+a, 'Y') for the model)
        # Bullet's hinge angle runs opposite to world +Y (checked: tumble test hit the lower limit), so mirror it
        c.limit_ang_z_lower, c.limit_ang_z_upper = -math.radians(OPEN_STOP - start), math.radians(start)
    else:                                      # detent: GENERIC, lock only rotation about local X = world +Y
        c.type = "GENERIC"
        c.use_limit_ang_x = True
        c.limit_ang_x_lower = c.limit_ang_x_upper = 0.0
        c.use_breaking, c.breaking_threshold = True, breaking
    return c


def build(f_hold, kinematic=True, pills=True, start_open=0.0):
    sc = reset()
    body = imp("models/sim/body.stl", "body")
    lid = imp("models/sim/lid.stl", "lid")
    for o in (body, lid):
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME")
        o.select_set(False)
    lid_mass = CFG["lid_mass_g"] * 1e-3 + (0 if pills else 0.010)
    rb(body, shape="MESH" if kinematic else "CONVEX_HULL", mass=CFG["body_mass_g"] * 1e-3, kin=kinematic)
    rb(lid, shape="CONVEX_HULL", mass=lid_mass)
    # lid hull fills its own pin hole -> it would jam on the body's pin. Put lid and body in separate
    # collision layers (layer 0 = body, 1 = lid); pills, finger and floor sit in both.
    body.rigid_body.collision_collections = [i == 0 for i in range(20)]
    lid.rigid_body.collision_collections = [i == 1 for i in range(20)]
    if start_open:
        R = Matrix.Rotation(math.radians(start_open), 4, "Y")
        piv = Vector((HX, HY, HZ))
        lid.matrix_world = Matrix.Translation(piv) @ R @ Matrix.Translation(-piv) @ lid.matrix_world
    constraint("hinge", body, lid, "hinge", start=start_open)
    lid["start"] = start_open
    det = None
    if f_hold > 0 and not start_open:
        dt = 1.0 / (FPS * SUB)
        det = constraint("detent", body, lid, "detent", breaking=f_hold * BEAD_LEVER * dt)
    if pills:
        r = CFG["pill_r"] * S
        for i, p in enumerate(CFG["pills"]):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=[c * S for c in p], segments=12, ring_count=6)
            o = bpy.context.active_object
            o.name = f"pill{i}"
            rb(o, shape="SPHERE", mass=0.010 / len(CFG["pills"]))
    return sc, body, lid, det


def lid_angle(body, lid, q0):
    q = body.matrix_world.to_quaternion().inverted() @ lid.matrix_world.to_quaternion() @ q0.inverted()
    ax, ang = q.to_axis_angle()
    a = math.degrees(ang) * (1 if ax.y > 0 else -1)
    a = a + lid.get("start", 0.0)
    return (a + 90.0) % 360.0 - 90.0          # range -90..270 (open stop is ~196)


def key_body(body, frames):
    """frames: list of (frame, loc_mm(x,y,z), euler_deg(x,y,z))"""
    body.rigid_body.kinematic = True
    base = body.location.copy()
    for f, loc, rot in frames:
        body.location = base + Vector(loc) * S
        body.rotation_euler = [math.radians(a) for a in rot]
        body.keyframe_insert("location", frame=f)
        body.keyframe_insert("rotation_euler", frame=f)


def run(sc, body, lid, n, render_tag=None):
    sc.frame_start, sc.frame_end = 1, n
    sc.rigidbody_world.point_cache.frame_start = 1
    sc.rigidbody_world.point_cache.frame_end = n
    sc.frame_set(1)
    q0 = lid.matrix_world.to_quaternion()
    q0 = body.matrix_world.to_quaternion().inverted() @ q0
    # headless frame_set alone does not step Bullet reliably -> bake the whole cache, then read it back
    bpy.ops.ptcache.free_bake_all()
    bpy.ops.ptcache.bake_all(bake=True)
    angs = []
    for f in range(1, n + 1):
        sc.frame_set(f)
        angs.append(lid_angle(body, lid, q0))
        if TRACE and f % 10 == 0:
            print(f"  f{f:4d} lid {angs[-1]:7.1f} deg  body rot {[round(math.degrees(a)) for a in body.matrix_world.to_euler()]}", flush=True)
        if render_tag and (f % VIDEO == 1 if VIDEO else f in (1, n // 3, 2 * n // 3, n)):
            render(sc, body, f"{render_tag}_{f:04d}")
    return angs


def render(sc, body, tag):
    cam = bpy.data.objects.get("cam")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        cam.name = "cam"
        sc.camera = cam
        bpy.ops.object.light_add(type="SUN", location=(0, 0, 1))
        try:
            sc.render.engine = "BLENDER_WORKBENCH"
        except TypeError:
            pass
        sc.render.resolution_x, sc.render.resolution_y = 640, 480
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "OBJECT"
        bpy.data.objects["lid"].color = (0.9, 0.4, 0.1, 1)
    c = body.matrix_world.translation
    cam.location = c + Vector((0.16, -0.16, 0.12))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(ROOT, "models/sim/renders", tag + ".png")
    bpy.ops.render.render(write_still=True)


def opened(angs, thr=3.0):
    return max(angs) > thr


results = []


def report(name, f, angs, extra=""):
    res = f"{name:38s} F_hold={f:>4.1f} N  lid angle min {min(angs):6.1f} max {max(angs):6.1f} end {angs[-1]:6.1f} deg -> " + \
          ("OPENED" if opened(angs) else "stayed closed") + extra
    print("RESULT", res, flush=True)
    results.append(res)


def arc(p_rel_mm, a0, a1, f0, f1, obj):
    piv = Vector((HX, HY, HZ))
    for f in range(f0, f1 + 1, 5):
        a = a0 + (a1 - a0) * (f - f0) / max(1, f1 - f0)
        obj.location = piv + Matrix.Rotation(math.radians(a), 3, "Y") @ (Vector(p_rel_mm) * S)
        obj.keyframe_insert("location", frame=f)


def finger(p_rel_mm):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.004, location=(0, 0, 0.1))
    f = bpy.context.active_object
    f.name = "finger"
    rb(f, shape="SPHERE", mass=0.1, kin=True)
    return f


FS = [float(x) for x in os.environ.get("ETIBOX_F", "0,5,10,15").split(",")]
for F in FS:
    tag = (lambda t: (t if RENDER else None))
    if want("flip"):   # 1 flip upside down slowly, hold, flip back
        sc, body, lid, det = build(F)
        key_body(body, [(1, (0, 0, 0), (0, 0, 0)), (60, (0, 0, 0), (180, 0, 0)), (200, (0, 0, 0), (180, 0, 0)), (260, (0, 0, 0), (360, 0, 0))])
        report("flip 180 + hold 1.4 s + flip back", F, run(sc, body, lid, 280, tag(f"flip_F{F:.0f}")))
    if want("tumble"):  # 2 two full turns on three axes (lid points every direction)
        sc, body, lid, det = build(F)
        key_body(body, [(1, (0, 0, 0), (0, 0, 0)), (100, (0, 0, 0), (360, 180, 90)), (200, (0, 0, 0), (720, 360, 180))])
        report("tumble 2 turns on 3 axes in 2 s", F, run(sc, body, lid, 220))
    for g_lvl, amp in ((3, 7.5), (8, 20.0)):   # 10 Hz: a = A*(2*pi*10)^2
        if want(f"shake{g_lvl}"):
            sc, body, lid, det = build(F)
            fr = [(1, (0, 0, 0), (0, 0, 0)), (30, (0, 0, 0), (180, 0, 0))]
            for kk in range(30):
                fr.append((40 + 5 * kk, (0, 0, amp if kk % 2 else -amp), (180, 0, 0)))
            key_body(body, fr)
            report(f"flip, then shake upside down {g_lvl} g 10 Hz", F, run(sc, body, lid, 200, tag(f"shake{g_lvl}_F{F:.0f}")))
    if want("drop"):    # 4 drop 1 m lid-up with pills: pills fly up into the lid on impact
        sc, body, lid, det = build(F, kinematic=False, pills=True)
        body.rigid_body.collision_shape = "MESH"
        for o in bpy.data.objects:
            o.location.z += 1.0
        bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.03))
        rb(bpy.context.active_object, typ="PASSIVE", shape="BOX")
        z0 = body.matrix_world.translation.z
        angs = run(sc, body, lid, 150)
        report("drop 1 m lid-up onto hard floor, pills", F, angs, f" | body fell {z0 - body.matrix_world.translation.z:.2f} m")


# 5 opening by finger (F_hold 5 N): finger under the free end swings the lid up to 120 deg, then pulls back
if want("open"):
    sc, body, lid, det = build(OPEN_F, pills=False)
    fg = finger((-40.0, 0.0, -7.2))
    arc((-40.0, 0.0, -7.2), 0, 0, 1, 20, fg)
    arc((-40.0, 0.0, -7.2), 0, 120, 20, 120, fg)
    arc((-40.0, 0.0, -7.2), 120, 0, 125, 200, fg)
    angs = run(sc, body, lid, 260, "open_finger" if RENDER else None)
    report("finger opens lid, lets go", OPEN_F, angs, f" | rests at {angs[-1]:.0f} deg (stop {OPEN_STOP:.0f})")

# 6 closing by finger: lid open at stop, finger pushes it down to closed
if want("close"):
    sc, body, lid, det = build(0.0, pills=False, start_open=OPEN_STOP - 1)
    fg = finger((-40.0, 0.0, 6.0))
    arc((-40.0, 0.0, 6.0), OPEN_STOP + 8, OPEN_STOP + 8, 1, 20, fg)
    arc((-40.0, 0.0, 6.0), OPEN_STOP + 8, 0, 20, 140, fg)
    angs = run(sc, body, lid, 180, "close_finger" if RENDER else None)
    report("finger closes lid", 0.0, angs, f" | ends at {angs[-1]:.1f} deg")

# 7 open lid must not fall shut: lid resting at the stop, tilt box +-30 deg and 3 g jiggle
if want("openhold"):
    sc, body, lid, det = build(0.0, pills=False, start_open=OPEN_STOP - 2)
    fr = [(1, (0, 0, 0), (0, 0, 0)), (60, (0, 0, 0), (0, 0, 0)),
          (100, (0, 0, 0), (0, 40, 0)), (130, (0, 0, 0), (0, 0, 0)), (170, (0, 0, 0), (0, -40, 0)), (200, (0, 0, 0), (0, 0, 0)),
          (220, (0, 0, 0), (40, 0, 0)), (240, (0, 0, 0), (0, 0, 0)), (260, (0, 0, 0), (-40, 0, 0)), (280, (0, 0, 0), (0, 0, 0))]
    for k in range(20):   # table knocks ~1.5 g (3 mm, ~11 Hz)
        fr.append((290 + 4 * k, (0, 0, 3 if k % 2 else -3), (0, 0, 0)))
    key_body(body, fr)
    angs = run(sc, body, lid, 380)
    ok = min(angs) > 60
    r = f"{'open lid, tilt +-40 deg each axis + 1.5 g knocks':34s} min lid angle {min(angs):6.1f} deg  -> " + ("stayed open" if ok else "FELL SHUT")
    print("RESULT", r, flush=True)
    results.append(r)

# 8 how far can the box tilt (toward closing) before an open lid falls shut?
if want("opentilt"):
    sc, body, lid, det = build(0.0, pills=False, start_open=OPEN_STOP - 1)
    key_body(body, [(1, (0, 0, 0), (0, 0, 0)), (20, (0, 0, 0), (0, 0, 0)), (320, (0, 0, 0), (0, -90, 0))])
    angs = run(sc, body, lid, 320)
    fall = next((f for f, a in enumerate(angs, 1) if a < OPEN_STOP - 10), None)
    tilt = None if fall is None else 90.0 * max(0, fall - 20) / 300.0
    r = f"{'open lid, slow tilt toward closing':34s} lid falls shut at box tilt ~{tilt if tilt is None else round(tilt)} deg"
    print("RESULT", r, flush=True)
    results.append(r)

open(os.path.join(ROOT, "models/sim/results.txt"), "w").write("\n".join(results) + "\n")
