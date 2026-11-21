"""Export body + one lid (closed pose) + pill start positions for the Blender rigid-body tests.
Run from repo root: python scripts/export_sim_parts.py  ->  models/sim/{body,lid}.stl, sim.json"""
import json, os, runpy
os.environ["ETIBOX_NO_EXPORT"] = "1"
g = runpy.run_path("scripts/make_etibox.py")
os.makedirs("models/sim", exist_ok=True)
g["body"].export("models/sim/body.stl")
lid = g["make_lid"]("noon")
lid.export("models/sim/lid.stl")

PILL_R = 4.0                                   # 8 mm pills
inner = g["pocket0"].buffer(-(PILL_R + 0.4))
pills = []
z = g["FLOOR"] + PILL_R + 0.3
while z + PILL_R < g["PLUG_Z0"] - 0.3:
    x0, y0, x1, y1 = inner.bounds
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            from shapely.geometry import Point
            if inner.contains(Point(x, y)):
                pills.append([x, y, z])
            y += 2 * PILL_R + 0.6
        x += 2 * PILL_R + 0.6
    z += 2 * PILL_R + 0.6
json.dump({"hinge": [g["XH"], 0.0, g["ZH"]], "pill_r": PILL_R, "pills": pills[:20],
           "lid_mass_g": lid.volume * 1.27e-3, "body_mass_g": g["body"].volume * 1.27e-3,
           "bead_r_mm": g["XH"] - g["T0"], "notch_r_mm": g["XH"] - g["T0"] - 3.0},
          open("models/sim/sim.json", "w"), indent=1)
print("pills", len(pills[:20]), "lid g", round(lid.volume * 1.27e-3, 2), "body g", round(g["body"].volume * 1.27e-3, 1))
