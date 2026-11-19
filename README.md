# etibox

A 6-compartment pill box with a flower-shaped body. Each compartment has its own hinged lid (print-in-place pin hinge). The model is generated from code, so every dimension is a parameter.

![license](https://img.shields.io/badge/license-MIT-blue)

## Files
- `models/etibox.stl` - ready-to-print model (body + 6 lids, lids printed standing open at 90°).
- `scripts/make_etibox.py` - parametric generator (trimesh + shapely + manifold3d).
- `scripts/check_etibox.py` - printability checks (bed fit, watertight, wall thickness, overhangs, rough bending stress).

## Print (tested target: Bambu Lab P1S)
- Material: PETG (or ASA). Avoid PLA for the hinge if you want it durable.
- 0.2 mm layers, 4 walls, 5 top/bottom layers, 30-40% gyroid infill.
- Print upright, no supports needed except possibly under the hinge columns; check the preview.
- After printing, fold each lid down by hand; the hinge has 0.35 mm clearance.
- Not a medical device. Clean before use and do not rely on it for dosing safety.

## Rebuild
```
pip install -r requirements.txt
# run from the repo root
python scripts/make_etibox.py
python scripts/check_etibox.py
```
Edit the constants at the top of the generator (wall, height, clearances, hinge size).

## Status
Printability checks currently report open issues (see Issues): some unsupported overhang area and non-watertight fragments in the check output. The model has not been physically test-printed yet.

## License
MIT, see `LICENSE`. Copyright (c) 2026 GIAMAT13.
