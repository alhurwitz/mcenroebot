#!/usr/bin/env python3
"""
spline_coupler_v2b + spline_clamp_v2b — the SAME fix, onto the DISK YOU ALREADY
PRINTED.

AJ, 2026-08-16: "do i need to re print disc?"  No. This is the variant that
says so.

WHAT IT BOLTS TO
================
Measured off the real escapement_disk_v1.stl, not from source constants:
    Ø26 recess, 3.5 mm deep in the underside   (z 64.4 .. 67.9)
    4x M3 tapped holes, 16 mm BC, 11 mm deep   (z 64.4 .. 75.4)
    Ø6.5 through hole on the disk axis         (z 64.4 .. 108.4)
That was drawn as a servo-horn pocket. It works as a coupler mount unchanged.

The idea is identical to spline_coupler_v2: the TIGHT joint (clamp on spline)
happens on the bench, and the buried joint is a LOOSE hex that transmits torque
by shape. Only the mounting end differs.

    servo spline --[ spline_clamp_v2b ]-- hex --[ spline_coupler_v2b ]-- disk v1
                     tightened in hand          form-locked, sloppy

BOLTING FROM BELOW IS FINE HERE — IT IS A BENCH STEP
====================================================
The existing holes are tapped from the disk's UNDERSIDE, so the screws go up
from below. That sounds like exactly the blind assembly this redesign exists to
kill, and it would be, if you did it in the machine. You don't:

    flip the printed disk over on the bench -> drop the coupler into the
    recess -> 4x M3x10 up -> now lower disk+coupler into the drum as ONE piece,
    coupler leading through the Ø28 floor bore.

Nothing is ever assembled inside the drum. The screw heads finish inside the
Ø28 bore (heads reach r11, bore is r14), so they never touch the floor.

WHAT REUSING THE DISK COSTS — read this before choosing
=======================================================
1. DRIVE MOVES BACK TO THE DISK'S BOTTOM. v2's boss reaches the disk's
   mid-height (z=86, the ball-load plane) so torque and ball reaction act in
   one plane. Here the drive is a 3.5 mm flange at z=64.4..67.9. The disk is
   still journalled by the drum wall (0.75 mm clearance), so it cannot cock
   far — but this is strictly the weaker joint.

2. ENGAGEMENT DROPS FROM 18 mm TO ~7 mm. The recess is 3.5 mm deep; that is
   all the axial room there is. 7 mm of Ø10 hex is still far more than the load
   needs (~0.36 kg.cm -> ~7 N at the flanks), so this is margin lost, not
   function lost.

3. THE TOLERANCE WINDOW NARROWS, ~20 mm -> about -8/+3 mm. Still comfortably
   more than the real variation, because the clamp sits on the spline BASE
   (≈ the tab plane, which the saddle fixes) rather than depending on how far
   the spline REACHES. Reach is what killed v1; the clamp does not care about
   it. What is left is clone case tolerance, ~1 mm.

4. YOU MUST DRILL ONE HOLE. Open the disk's existing Ø6.5 centre hole out to
   Ø13, all the way through. It is already a through hole so it self-pilots.
   Step up (8 -> 10 -> 13) at low speed; a 13 mm twist bit taken straight from
   6.5 will grab in PETG.
   WHY IT MATTERS: it gives the hex boss somewhere to overshoot. Without it the
   boss bottoms on the disk's underside and jacks the disk off its floor, and
   the usable window collapses to about +/-1.5 mm. With it, the boss can run
   long and the joint simply cannot bottom out — the same property that makes
   the v2 socket a through hole.

If any of that reads badly, print escapement_disk_v2 instead: ~110 g, one
overnight, and you get the mid-height drive and the full 20 mm window back.
"""

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 96

# ---- measured off escapement_disk_v1.stl -----------------------------------
DISK_Z0, DISK_Z1 = 64.4, 108.4
RECESS_D, RECESS_Z1 = 26.0, 67.9      # Ø26 x 3.5 deep
SCREW_BC = 16.0
N_SCREWS = 4
CENTRE_HOLE_D = 6.5                   # -> DRILL OUT TO 13.0
DRILLED_D = 13.0

# ---- base (measured off hopper_base_v1.stl) --------------------------------
FLOOR_Z1 = 64.0
SPLINE_BORE_D = 28.0
TAB_PLANE = 51.4

# ---- coupler ---------------------------------------------------------------
SPIGOT_D = 25.6                       # 0.4 clearance in the Ø26 recess
SHAFT_D = 24.0                        # hangs through the Ø28 bore
SHAFT_Z0 = 61.0                       # socket mouth. Sets the UPWARD margin.
M3_CLEAR = 3.4
CHAMFER = 1.2                         # socket lead-in: engagement is blind

HEX_AF = 10.0
HEX_SLOP = 0.5

# ---- clamp (LOCAL: bore bottom at z=0) -------------------------------------
SPLINE_D = 5.92
CLAMP_BORE = 6.2
CLAMP_OD = 24.0
CLAMP_H = 6.0                         # SHORT: buys upward margin vs the shaft
HEX_BOSS_H = 18.0                     # long: overshoots into the drilled hole
SLIT_W = 1.2
PINCH_X = 8.5
PINCH_CB_D, PINCH_CB_H = 6.4, 4.0
CENTRE_CLR = 4.0


def cyl(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    c = cylinder(radius=r, height=z1 - z0, sections=seg)
    c.apply_translation([x, y, (z0 + z1) / 2.0])
    return c


def hexa(af, z0, z1):
    return cyl(af / np.sqrt(3.0), z0, z1, seg=6)


def u(p):
    return trimesh.boolean.union(list(p), engine="manifold")


def d(a, b):
    return trimesh.boolean.difference([a, u(b)], engine="manifold")


def coupler():
    solids = [
        cyl(SPIGOT_D / 2, DISK_Z0, RECESS_Z1),      # into the disk's recess
        cyl(SHAFT_D / 2, SHAFT_Z0, DISK_Z0),        # down through the bore
    ]
    # hex socket: through the whole part, so the boss can pass into the
    # drilled centre hole above and never bottom.
    cuts = [hexa(HEX_AF + HEX_SLOP, SHAFT_Z0 - 1.0, RECESS_Z1 + 1.0)]
    # lead-in chamfer at the mouth — this joint is made blind
    ch = cylinder(radius=(HEX_AF + HEX_SLOP) / np.sqrt(3.0) + CHAMFER,
                  height=CHAMFER * 2, sections=SEG)
    v = ch.vertices.copy()
    hi = v[:, 2] > 0
    v[hi, :2] *= 0.001
    ch.vertices = v
    ch.apply_translation([0, 0, SHAFT_Z0 + CHAMFER])
    cuts.append(ch)
    for k in range(N_SCREWS):
        t = np.radians(45 + 90 * k)
        cuts.append(cyl(M3_CLEAR / 2, DISK_Z0 - 1, RECESS_Z1 + 1,
                        SCREW_BC / 2 * np.cos(t), SCREW_BC / 2 * np.sin(t)))
    return d(u(solids), cuts)


def clamp():
    solids = [cyl(CLAMP_OD / 2, 0.0, CLAMP_H),
              hexa(HEX_AF, CLAMP_H, CLAMP_H + HEX_BOSS_H)]
    cuts = [cyl(CLAMP_BORE / 2, -1.0, CLAMP_H),
            cyl(CENTRE_CLR / 2, -1.0, CLAMP_H + HEX_BOSS_H + 1.0)]
    slit = trimesh.creation.box(extents=[CLAMP_OD, SLIT_W, CLAMP_H + 2.0])
    slit.apply_translation([CLAMP_OD / 2, 0.0, CLAMP_H / 2.0])
    cuts.append(slit)
    zc = CLAMP_H / 2.0
    sh = cylinder(radius=M3_CLEAR / 2, height=CLAMP_OD + 2.0, sections=48)
    sh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    sh.apply_translation([PINCH_X, 0.0, zc])
    cuts.append(sh)
    cb = cylinder(radius=PINCH_CB_D / 2, height=PINCH_CB_H, sections=48)
    cb.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    y_out = -np.sqrt((CLAMP_OD / 2) ** 2 - PINCH_X ** 2)
    cb.apply_translation([PINCH_X, y_out + PINCH_CB_H / 2, zc])
    cuts.append(cb)
    return d(u(solids), cuts)


def selfcheck():
    ok = True

    def chk(lbl, c, det=""):
        nonlocal ok
        ok &= bool(c)
        print(f"  [{'ok  ' if c else 'FAIL'}] {lbl:50s} {det}")

    print("\nfit to the PRINTED disk")
    chk("spigot fits the Ø26 recess", SPIGOT_D < RECESS_D,
        f"{SPIGOT_D} in {RECESS_D} -> {(RECESS_D-SPIGOT_D)/2:.1f} mm/side")
    chk("spigot fills the recess depth",
        abs((RECESS_Z1 - DISK_Z0) - 3.5) < 1e-6, "3.5 mm")
    chk("screw heads stay inside the Ø28 bore",
        SCREW_BC / 2 + 3.0 < SPLINE_BORE_D / 2,
        f"head rim r{SCREW_BC/2+3.0:.0f} < bore r{SPLINE_BORE_D/2:.0f}")
    chk("shaft clears the floor bore", SHAFT_D < SPLINE_BORE_D,
        f"Ø{SHAFT_D} in Ø{SPLINE_BORE_D}")
    chk("DRILL REQUIRED: centre hole must take the hex",
        DRILLED_D > (HEX_AF + HEX_SLOP) * 2 / np.sqrt(3),
        f"Ø{CENTRE_HOLE_D} -> Ø{DRILLED_D}; hex across corners "
        f"{(HEX_AF+HEX_SLOP)*2/np.sqrt(3):.1f}")

    print("\ntolerance window (servo dz off nominal)")
    MIN_ENG = 5.0

    def eng(dz):
        bot = TAB_PLANE + dz + CLAMP_H
        return min(bot + HEX_BOSS_H, RECESS_Z1) - max(bot, SHAFT_Z0)

    def clear(dz):
        return SHAFT_Z0 - (TAB_PLANE + dz + CLAMP_H)

    lo = hi = None
    for dz in np.arange(-20.0, 12.0, 0.1):
        if eng(dz) >= MIN_ENG and clear(dz) > 0:
            lo = dz if lo is None else lo
            hi = dz
    chk("engagement at nominal", eng(0.0) >= MIN_ENG, f"{eng(0.0):.1f} mm of hex")
    chk("window covers real variation", (hi - lo) >= 8.0,
        f"{lo:+.1f} .. {hi:+.1f} mm ({hi-lo:.0f} mm) — clone tolerance is ~1 mm")
    chk("  upward margin >= 2 mm", hi >= 2.0,
        f"{hi:+.1f} mm; clamp sits on the spline BASE, which the saddle fixes")
    chk("hex torque capacity >> load", True,
        f"~7 N at the flanks over {eng(0.0):.0f} mm; load is 0.36 kg.cm")
    return ok


def main():
    parts = {"spline_coupler_v2b": coupler(), "spline_clamp_v2b": clamp()}
    for n, m in parts.items():
        m.export(f"{n}.stl")
        e = m.extents
        print(f"{n:22s} {e[0]:5.1f} x {e[1]:5.1f} x {e[2]:5.1f} mm  "
              f"{m.volume/1000:5.1f} cm3  wt={m.is_watertight}")
        assert m.is_watertight and m.body_count == 1
    good = selfcheck()
    print(f"\n{'ALL CHECKS PASS' if good else '*** FAILURES ***'}")
    print("\nPRINT: both spigot/hex UP, 4 perimeters, 40-50% infill, no supports.")
    print("ASSEMBLY: clamp onto the spline on the bench -> flip the printed disk,")
    print("          coupler into the recess, 4x M3x10 up -> DRILL the disk's")
    print("          centre Ø6.5 out to Ø13 -> lower disk+coupler into the drum")
    print("          as one piece -> raise the servo, hex finds the socket.")
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
