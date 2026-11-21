# etibox

A 6-compartment pill box with a flower-shaped body. Each compartment has its own hinged lid (print-in-place pin hinge) that locks with a hook latch, so the box can be flipped, shaken or dropped without spilling. Every lid has the same large handle, made to be easy for adults and older people. The model is generated from code, so every dimension is a parameter.

![license](https://img.shields.io/badge/license-MIT-blue)

## Files
- `models/etibox_all_white.stl` - single-colour print: body + 6 lids (lids print standing open at 90°), symbols engraved.
- `models/etibox_white_part.stl` + `models/etibox_black_part.stl` - the same split for two-colour printing (black symbol inlays).
- `models/etibox_detent_coupon.stl` - calibration plate, see below.
- `scripts/make_etibox.py` - parametric generator (trimesh + shapely + manifold3d).
- `scripts/check_etibox.py` - print and strength checks.
- `scripts/test_lid.py` - lid swing sweep, open stop, print clearance.
- `scripts/sim_blender.py` - Blender (Bullet) rigid-body tests: flip, tumble, shake, drop, open, close, tilt.
- `scripts/ramguard.py` - runs a command and stops it if system RAM goes above 90%.

## Print (target: Bambu Lab P1S)
- Material: PETG. PLA is too brittle for the latch tongue and hinge.
- 0.2 mm layers, 4 walls, 5 top/bottom layers, 30-40% gyroid infill.
- Print upright, no supports. The only bridges are the hinge pins (11 mm span).
- After printing, fold each lid down by hand (0.35 mm hinge clearance) and press it shut until the latch clicks.
- Not a medical device. Clean before use and do not rely on it for dosing safety.

## How the lid locks and opens
- A springy tongue stands in the centre of the box next to each compartment. Its lip hooks over a tab on the lid. The tongue stands upright, so it bends along the printed layers (the strong direction).
- **Close:** press the lid down. The tab pushes the 45° ramp aside and the lip clicks over it (~9 N, one finger).
- **Open:** push the wide release lever (8 x 5 mm, a whole fingertip, no fingernail) toward the centre, then lift the lid by its grip fin (12 x 4.5 mm, pinch it between thumb and finger). The handle is the same on every lid.
- Pulling on a locked lid does not open it: the lip face is flat, so it does not cam open. It holds a 50 N pull with 3x safety.
- Open, the lid swings over to ~196° and rests against the outside of the box, so it does not fall shut while you fill it.

## Test results
`check_etibox.py` (all pass): fits the bed, watertight, no wall under 1.2 mm, no unsupported overhang, tongue peak strain 1.8% (PETG yields ~4%), click force 8.9 N, lip safety 3.1x at 50 N, rim wall safety 7x, hinge pin safety 2.8x at a 20 N pull, lid arm safety 19x.

`test_lid.py`: no collision 0-194°, open stop ~196°, print-pose clearance 0.35 mm.

Blender, holding force (F_hold = force before the lid lets go):

| Test | 0 N (no lock) | 5 N | 10 N | 15 N |
|---|---|---|---|---|
| Flip 180° and back | opens | holds | holds | holds |
| Tumble, 2 turns on 3 axes | opens | holds | holds | holds |
| Upside down, 3 g shake | opens | opens | holds | holds |
| Upside down, 8 g shake | opens | opens | holds | holds |
| 1 m drop on a hard floor | opens | opens | holds | holds |

The hook latch holds far more than 15 N, so it passes every test. Opening with a finger swings the lid to its 196° rest; closing with a finger shuts it. An open lid stays open through ±40° tilts with knocks.

Watch a test live in Blender: `blender --python scripts/show_blender.py -- flip 20` (also tumble, shake3, shake8, drop, open, close).

## Calibration coupon
`models/etibox_detent_coupon.stl`: one compartment and lid each with lip overlap 0.3 / 0.5 / 0.7 / 0.9 mm. Print it in your PETG and keep the one that clicks firmly and still releases easily. Then rebuild with it: `ETIBOX_LATCH=0.7 python scripts/make_etibox.py`.

## Rebuild
```
pip install -r requirements.txt
# run from the repo root
python scripts/make_etibox.py
python scripts/check_etibox.py
python scripts/test_lid.py
python scripts/export_sim_parts.py
blender -b --factory-startup --python scripts/sim_blender.py
```

## Status
All checks pass in software. Not yet test-printed.

## License
MIT, see `LICENSE`. Copyright (c) 2026 GIAMAT13.
