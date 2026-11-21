# etibox

A 6-compartment pill box with a flower-shaped body. Each compartment has its own hinged lid (print-in-place pin hinge) that clicks shut with a snap bead, so the box can be flipped, shaken or dropped without spilling. The model is generated from code, so every dimension is a parameter.

![license](https://img.shields.io/badge/license-MIT-blue)

## Files
- `models/etibox_all_white.stl` - single-colour print: body + 6 lids (lids print standing open at 90°), symbols engraved.
- `models/etibox_white_part.stl` + `models/etibox_black_part.stl` - the same split for two-colour printing (black symbol inlays).
- `models/etibox_detent_coupon.stl` - calibration plate, see below.
- `scripts/make_etibox.py` - parametric generator (trimesh + shapely + manifold3d).
- `scripts/check_etibox.py` - print and strength checks.
- `scripts/test_lid.py` - lid swing sweep, open stop, print clearance, snap passage.
- `scripts/sim_blender.py` - Blender (Bullet) rigid-body tests: flip, tumble, shake, drop, open, close, tilt.
- `scripts/ramguard.py` - runs a command and stops it if system RAM goes above 90%.

## Print (target: Bambu Lab P1S)
- Material: PETG. PLA is too brittle for the snap and hinge.
- 0.2 mm layers, 4 walls, 5 top/bottom layers, 30-40% gyroid infill.
- Print upright, no supports. The only bridges are the hinge pins (11 mm span).
- After printing, fold each lid down by hand (0.35 mm hinge clearance) and press it shut until it clicks.
- Not a medical device. Clean before use and do not rely on it for dosing safety.

## How the lid locks
- Under each lid is a 1.2 mm skirt with a 45° bead (0.55 mm). It snaps into a matching groove in the pocket wall: 0.25 mm interference while passing, 0.1 mm play when seated.
- A fingernail notch at the centre end of each lid lets you lift it.
- Open, the lid swings over to ~196° and rests against the outside of the box, so it does not fall shut while you fill it.

## Test results
`check_etibox.py`: fits the bed, watertight, no wall under 1.2 mm, no unsupported overhang, snap peak strain 1.5% (PETG yields ~4%), rim wall safety 7x, hinge pin safety 2.8x at a 20 N pull, lid arm safety 19x.

`test_lid.py`: no collision 0-194°, open stop ~196°, print-pose clearance 0.35 mm. The far end of the skirt swings on an arc and pushes in 0.43 mm while snapping (~2.6% strain, still under yield).

Blender, holding force needed (F_hold = force at the bead before the lid lets go):

| Test | 0 N (old design) | 5 N | 10 N | 15 N | 20 N |
|---|---|---|---|---|---|
| Flip 180° and back | opens | holds | holds | holds | holds |
| Tumble, 2 turns on 3 axes | opens | holds | holds | holds | holds |
| Upside down, 3 g shake | opens | holds | holds | holds | holds |
| Upside down, 8 g shake | opens | opens | holds | holds | holds |
| 1 m drop on a hard floor | opens | opens | opens | opens | holds |

Everyday use (flip, bag, shaking) needs ~10 N; surviving a 1 m drop needs ~20 N. Videos: `models/sim/*.gif`.
At 15 N a finger still opens the lid, which then rests at 196°. Closing by finger reaches 0°. An open lid stays open through ±40° tilts with knocks.

Plastic stiffness is only estimated, so print the coupon first.

## Calibration coupon
`models/etibox_detent_coupon.stl`: one compartment and lid each with bead 0.45 / 0.55 / 0.65 / 0.75 mm. Print it in your PETG, flip and shake each one, and keep the bead that clicks firmly but still opens with one fingernail. Then rebuild with it: `ETIBOX_BEAD=0.65 python scripts/make_etibox.py`.

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
