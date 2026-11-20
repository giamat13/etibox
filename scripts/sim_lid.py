"""Lid retention simulation (flip / rotate / shake / drop) for the snap detent.
Rigid-lid dynamics about the hinge axis with gravity in every box orientation plus acceleration
pulses. Output = holding force the detent must supply at the bead, per scenario, and whether a given
detent strength survives (lid angle after the event). Detent strength is a parameter because plastic
stiffness is not simulated - calibrate with models/etibox_detent_coupon.stl. Run from repo root."""
import math, os, runpy
import numpy as np

os.environ["ETIBOX_NO_EXPORT"] = "1"
g = runpy.run_path("scripts/make_etibox.py")
lid = g["make_lid"]("noon")
XH, ZH = g["XH"], g["ZH"]
RHO = 6.0                                  # density g/cm3 -> use PETG 1.27 g/cm3
PETG = 1.27e-3                             # g/mm3
m_lid = lid.volume * PETG / 1000.0         # kg
cg = lid.center_mass
lever = math.hypot(cg[0] - XH, cg[2] - ZH) * 1e-3   # m, CG to hinge axis
PILLS = 0.010                              # kg of pills resting on lid when inverted (10 g, worst case)
rho_bead = 0.040                           # m, bead distance from hinge (far end of pocket ~ 40-47 mm)
m = m_lid + PILLS
I = m_lid * (lever ** 2 + (0.016) ** 2) + PILLS * lever ** 2   # rough

print(f"lid mass {m_lid*1000:.1f} g, CG lever {lever*1000:.1f} mm, load incl. pills {m*1000:.1f} g")
print("\nRequired detent holding force at the bead (N), lid closed, worst orientation (box upside down):")
cases = [("static, box flipped (1 g)", 1), ("walking in a bag (3 g)", 3), ("vigorous shake (8 g)", 8),
         ("knocked on table (20 g)", 20), ("dropped ~1 m onto floor (100 g)", 100)]
req = {}
for name, a in cases:
    F = m * a * 9.81 * lever / rho_bead
    req[name] = F
    print(f"  {name:36s} {F:6.2f} N")


def simulate(F_hold, accel_g, pulse_ms, ori_deg, dt=2e-5):
    """Lid angle (deg) reached after a pulse. ori: 0 = box upright (lid on top, gravity closes), 180 = upside down.
    Detent torque holds while angle < 1.5 deg; once past it, nothing resists (no hinge friction assumed = worst case)."""
    th, w, t = 0.0, 0.0, 0.0
    tau_hold = F_hold * rho_bead
    g0 = 9.81
    while t < 0.6:
        a = accel_g * g0 * (math.sin(math.pi * t / (pulse_ms * 1e-3)) if t < pulse_ms * 1e-3 else 0.0)
        ax = g0 * math.cos(math.radians(ori_deg)) + a              # push of load away from closed position
        tau_load = m * ax * lever * math.cos(th) - m * 0 - 0.0     # opens lid when ax > 0 (box inverted / lid thrown)
        if th < math.radians(1.5):
            tau_net = tau_load
            if tau_net <= tau_hold:
                tau_net = 0.0
            else:
                tau_net -= tau_hold
        else:
            tau_net = tau_load
        w += tau_net / I * dt
        th = max(th + w * dt, 0.0)
        if th == 0.0 and w < 0:
            w = 0.0
        t += dt
        if th > math.radians(80):
            break
    return math.degrees(th)


print("\nResult for candidate detent strengths (lid angle after event, deg; >2 = lid opened):")
print("  event: upside-down 1 g hold, 8 g shake 20 ms, 20 g knock 5 ms, 100 g drop 2 ms")
for F in (0.5, 2.0, 5.0, 10.0):
    r = [simulate(F, 0, 20, 180), simulate(F, 8, 20, 180), simulate(F, 20, 5, 180), simulate(F, 100, 2, 180)]
    print(f"  F_hold {F:5.1f} N:", "  ".join(f"{x:6.1f}" for x in r))
# opening by finger: finger force on the knob (radius ~ 0.045 m from hinge)
knob_r = (g["XH"] - (g["X_POCKET"] - 8.0)) * 1e-3
print(f"\nFinger opening force on the knob at F_hold=5 N: {5.0*rho_bead/knob_r:.1f} N "
      f"(comfortable <= ~15 N, hard above ~25 N)")
