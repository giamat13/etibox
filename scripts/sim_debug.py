"""Debug: does a POINT/HINGE constraint swing a simple cube? and the lid with BOX/hull shapes?"""
import os, runpy, math
os.environ["ETIBOX_ONLY"] = "__none__"
m = runpy.run_path(os.path.join(os.getcwd(), "scripts/sim_blender.py"))
reset, rb, build = m["reset"], m["rb"], m["build"]
import bpy


def swing(sc, obj, n=31):
    sc.frame_start, sc.frame_end = 1, n
    sc.rigidbody_world.point_cache.frame_start = 1
    sc.rigidbody_world.point_cache.frame_end = n
    p0 = obj.matrix_world.translation.copy()
    for f in range(1, n + 1):
        sc.frame_set(f)
    return [round(v, 1) for v in (obj.matrix_world.translation - p0) * 1000]


for ctype in ("POINT", "HINGE"):
    sc = reset()
    bpy.ops.mesh.primitive_cube_add(size=0.04, location=(0, 0, 0.2))
    anchor = bpy.context.active_object
    rb(anchor, typ="PASSIVE", shape="BOX")
    bpy.ops.mesh.primitive_cube_add(size=0.01, location=(0.03, 0, 0.25))
    cube = bpy.context.active_object
    rb(cube, shape="BOX", mass=0.01)
    e = bpy.data.objects.new("c", None)
    sc.collection.objects.link(e)
    e.location = (0, 0, 0.25)
    e.rotation_euler = (-math.pi / 2, 0, 0)
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = e
    bpy.ops.rigidbody.constraint_add()
    c = e.rigid_body_constraint
    c.type, c.object1, c.object2 = ctype, anchor, cube
    print("F cube", ctype, "moved mm", swing(sc, cube))

# lid itself, POINT pivot, with different shapes / masses
for shape in ("CONVEX_HULL", "BOX"):
    sc, body, lid, det = build(0.0, pills=False, start_open=60)
    lid.rigid_body.collision_shape = shape
    bpy.data.objects["hinge"].rigid_body_constraint.type = "POINT"
    print("G lid", shape, "scale", tuple(round(s, 4) for s in lid.scale), "dims mm", [round(d * 1000, 1) for d in lid.dimensions],
          "moved mm", swing(sc, lid))
