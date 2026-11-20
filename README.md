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

## Lid lock (snap detent)
Each lid has a chamfered bead that clicks into a groove in the pocket wall, so the box stays shut when flipped or shaken.
- `scripts/sim_lid.py` - lid dynamics: required holding force per event (flip 0.1 N, 8 g shake 0.7 N, 20 g knock 1.7 N, 1 m drop 8.6 N). A detent of ~3-5 N survives all but the drop at 5 N, and still opens with ~9-14 N finger force.
- `scripts/test_lid.py` - lid swing sweep, no collision with the body from 0 to 90 deg.
- `models/etibox_detent_coupon.stl` - calibration plate: one compartment printed with bead 0.35/0.45/0.55/0.65 mm. Print it first (PETG), keep the bead that clicks firmly and opens with one finger, set `ETIBOX_BEAD` (default 0.55) and rebuild.
- Plastic stiffness is not simulated; the coupon is the real test.

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
