"""Open the Blender window and play one lid test live.
Run from repo root:
  blender --python scripts/show_blender.py -- flip 20
Scenario: flip | tumble | shake3 | shake8 | drop | open | close | openhold | opentilt. Second value: holding force in N
(0 = the old design without a lock)."""
import bpy, os, sys

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scen = args[0] if args else "flip"
force = args[1] if len(args) > 1 else "20"
os.environ.update(ETIBOX_SHOW="1", ETIBOX_ONLY=scen, ETIBOX_F=force, ETIBOX_OPEN_F=force)
SIM = os.path.join(os.getcwd(), "scripts/sim_blender.py")


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                region = next(r for r in area.regions if r.type == "WINDOW")
                return win, area, region
    return None


def run():
    found = view3d()
    if not found:
        return 0.5  # UI not ready yet, try again
    win, area, region = found
    sys.argv = [sys.argv[0]]
    # stl_import needs a real window context; the startup script context has none
    with bpy.context.temp_override(window=win, area=area, region=region):
        exec(compile(open(SIM).read(), "sim_blender.py", "exec"), {"__name__": "__main__"})
        lid = bpy.data.objects.get("lid")
        if lid:
            lid.color = (0.9, 0.4, 0.1, 1)
        sp = area.spaces.active
        sp.shading.type = "SOLID"
        sp.shading.color_type = "OBJECT"
        sp.overlay.show_floor = False
        bpy.ops.view3d.view_all(center=False)
        sp.region_3d.view_distance = 0.35
        bpy.context.scene.frame_set(1)
        bpy.ops.screen.animation_play()
    return None


bpy.app.timers.register(run, first_interval=1.5)
