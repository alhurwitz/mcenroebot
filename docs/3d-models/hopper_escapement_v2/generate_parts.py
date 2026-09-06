#!/usr/bin/env python3
"""
hopper_escapement_v2 — drive-train redesign. Makes the servo joint assemblable.

WHY v2 EXISTS
=============
v1's mechanism is right and is NOT changed here. What is changed is how torque
gets from the MG996R into escapement_disk. That joint failed three times:

  2026-07-25  SV_TAB_TO_HORN = 13.0 was a guess. The spline never reached the
              horn recess in the disk underside. -> spline_coupler_v1.
  2026-08-16  drive_rod_v1: a 30 mm slip socket that tolerated the unmeasured
              SPAN. AJ: "it slides in and off rather than being tight."
  (implied)   the tight version needs a press bore, which needs a fit coupon,
              which needs another round trip.

Three failures, one root cause, and it is not any of the individual numbers:

    THE TIGHT JOINT WAS BURIED WHERE NOBODY CAN SEE OR REACH IT.

A coaxial coupling inside a Ø28 bore, under a 44 mm drum floor, beneath a
568 cm3 disk, has to be dimensionally perfect BEFORE assembly, because there is
no way to adjust it afterwards. Every fix that keeps it there inherits the
problem. So v2 does not make a better buried joint. It moves the joint out.

THE MOVE
========
Split the coupling in two at the point where the requirements conflict:

    servo spline --[ spline_clamp_v2 ]-- hex --[ spline_coupler_v2 ]-- disk
                     TIGHT, adjustable            LOOSE, form-locked
                     done on the BENCH            slides together blind

  The split is also PHYSICAL, and that matters more than it looks. The clamp
  lives in the base's Ø28 floor bore and pokes its hex UP through the floor.
  The coupler lives entirely ABOVE the floor, inside the disk. Nothing but a
  Ø10 hex ever crosses the floor plane. A first cut had both parts at Ø24
  sharing the same 12 mm of bore — they collided, and the section drawing is
  what caught it. Keeping them on opposite sides of the floor means neither
  one can grow into the other's space later.

  * `spline_clamp_v2` is a split clamp that grips the spline. It is tightened
    OFF THE MACHINE, in your hand, where you can see it and put real torque on
    it. Being a clamp and not a press fit, it does not care what your printer
    does to hole diameters — you tighten it until it grips. The fit coupon is
    no longer on the critical path.

  * `spline_coupler_v2` is screwed to the disk from ABOVE (your ask) and ends
    in a 14 mm HEX SOCKET that simply drops over the clamp's hex boss. That
    joint is deliberately SLOPPY — 0.6 mm across flats. It transmits torque by
    SHAPE, so slop costs nothing, and it engages blind because a hex finds its
    own orientation in at most 60 deg of wiggle.

  * The socket is 24 mm deep over a 16 mm boss, so engagement depth is free
    over ~8 mm. THAT IS WHAT KILLS SPAN. The unknown gap between the spline and
    the disk is no longer a dimension anybody has to know — it is just how far
    the hex happens to sit in its socket.

Every one of AJ's four stated pains maps onto one of these moves:
  can't see or reach it   -> the tight joint is now a bench operation
  fits must be exact      -> clamp is adjustable, hex is form-locked
  fiddly fasteners        -> 1 pinch bolt + 4 top screws, no inserts, no grubs
  servo not removable     -> pull the servo down; the hex just disengages

WHAT ELSE CHANGED, AND WHY
==========================
1. THE DISK NOW RIDES ON THE FLOOR (DISK_GAP 0.4 -> 0).
   In v1 the disk HUNG from the servo spline, which is why SV_TAB_TO_HORN was
   critical at all — it set how hard the disk was pressed onto the floor. Let
   the floor carry the disk and that dimension stops mattering. Cost is
   friction, and the friction is negligible: ~0.19 kg (disk + ball) on a FLAT
   face, mean radius 45.3 mm, mu~0.3 -> 0.26 kg.cm against an MG996R's ~10.
   The underside is deliberately flat — see the note by the disk constants for
   why the obvious "relieve it to a narrow land" move makes both the friction
   and the print worse.

2. THE COUPLER BOSS RUNS UP TO THE DISK'S MID-HEIGHT (z=86).
   AJ 2026-08-16: "making spline attachment extend upwards, so the disc sits in
   middle of ball." Correct and adopted. Ball centre is z=84, disk mid is 86 —
   drive torque and ball reaction now act in the same plane, so the disk cannot
   cock about a shallow flange the way a bottom-mounted horn lets it.

3. DISK_T STAYS AT 44. AJ proposed thinning it; that breaks the mechanism.
   The disk top face IS the shear plane: the queued ball under the throat must
   rest on it rather than on the carried ball. Carried ball sits on the floor
   (z=64) so its crown is at 104. Any disk top below 104 and the queued ball
   lands on the carried ball and follows it out — double feed. Centres must be
   40 apart to clear; at 28 mm of vertical offset that needs 28.6 mm of lateral
   travel, which is far more than the pocket has moved when the queued ball
   commits. Hence DISK_T >= BALL, exactly as v1's own comment says. check.py
   asserts this so nobody thins it again by eye.

KEPT, NOT REPRINTED
===================
hopper_base_v1 (805 cm3) and hopper_cone_v1 (199 cm3) are UNCHANGED and stay on
the machine. AJ authorised a clean sheet; this does not spend it, because the
base was never what was broken — its Ø28 spline bore and open-from-below servo
cavity are exactly what v2 needs. drum_lid_v1 is unchanged too (still unprinted;
print it as-is). Reprinting 805 cm3 to fix a coupling is not a trade worth
making. All v2 geometry below is verified against the REAL hopper_base_v1.stl
by check.py, not against v1's source constants.

FRAME: identical to v1. Origin at the chute axis on the bracket coupler
flange's top face; launcher(x,y,z) = (X-60, Y+49, Z+156). +Z up.
Disk and coupler are modelled IN PLACE (absolute z, so they cross-check against
the staged base). The clamp is modelled at LOCAL origin because its absolute
height is set by the servo's real spline reach, which is precisely the number
this design refuses to depend on.
"""

import numpy as np
import trimesh
from trimesh.creation import box, cylinder

SEG = 96

# ---------------- locked from v1 / verified against hopper_base_v1.stl -------
BALL = 40.0
BORE_D = 46.0                 # DISCH drop bore, ball + 3 mm clearance
R_P = 40.0                    # pocket orbit radius
DISK_D = 136.0
DISK_T = 44.0                 # >= BALL. This is the shear plane. Do not thin.
POCKET_D = 44.0
FLOOR_Z1 = 64.0               # drum floor top  (measured off the base STL)
SPLINE_BORE_D = 28.0          # base's bore through the floor (measured)
TAB_PLANE = 51.4              # servo-cavity ceiling / saddle top (measured)
LID_Z0 = 109.4                # lid underside   (measured off the lid STL)
DISK_AX = np.array([-R_P, 0.0])
CHUTE_AX = np.array([0.0, 0.0])

M3_CLEAR = 3.4
M3_TAP = 2.5                  # self-tap pilot in PETG
M3_HEAD_D = 6.0

# ---------------- v2: the disk rides on the floor ---------------------------
DISK_Z0 = FLOOR_Z1            # was FLOOR_Z1 + 0.4 (hung from the servo)
DISK_Z1 = DISK_Z0 + DISK_T    # 108.0
DISK_MID = (DISK_Z0 + DISK_Z1) / 2.0   # 86.0 — ball centre is 84
# NO UNDERSIDE RELIEF — worth writing down, because the first cut had one
# (0.4 mm deep inside r60, leaving an r60..68 bearing land) and it was wrong on
# BOTH counts it was meant to help.
#
# 1. IT INCREASES FRICTION. Sliding thrust torque follows the area-weighted mean
#    radius, (2/3)(ro^3-ri^3)/(ro^2-ri^2), NOT contact area. Pushing contact out
#    to an r60..68 ring moves that radius 45.3 -> 64.1 mm, i.e. 0.26 -> 0.36
#    kg.cm. The "relieve it to reduce area" instinct is backwards here.
# 2. IT IS UNPRINTABLE FACE-DOWN. The disk prints underside-on-the-bed, so a
#    0.4 mm relief across r<60 is a 120 mm unsupported span sitting 0.4 mm off
#    the glass on layer one. It droops onto the bed.
#
# Flat is lower friction, prints perfectly, and gives the largest possible
# first-layer footprint on a 550 cm3 part. Anti-suction was the only argument
# for a land, and PETG on PETG with ball dust between them does not suction.

# ---------------- v2: coupler — lives ENTIRELY ABOVE THE FLOOR --------------
# Nothing of the coupler enters the base's Ø28 bore. That bore belongs to the
# clamp. Only the Ø10 hex crosses z=64.
# 4 mm off the floor. Not for rub clearance — that only needs 0.5 — but to
# open a gap the CLAMP BODY can grow into. The clamp's Ø24 body must stay below
# the coupler (only the hex may enter it), and the clamp's height above the
# floor is set by the servo's real spline reach, which nobody has measured.
# Raising the coupler buys ~6.6 mm of "servo sits higher than expected" margin
# for free.
COUPLER_Z0 = 68.0
BOSS_D = 27.0                 # constant OD, inside the disk's counterbore
BOSS_FIT = 0.3
N_SCREWS = 4
SCREW_BC = 20.0               # r10 — OUTBOARD of the hex socket, so socket
                              # depth and screw engagement stop competing
SCREW_ENGAGE = 12.0           # tap depth, DISK_MID down to 74

HEX_AF = 10.0                 # small on purpose: the load is ~0.4 kg.cm, and a
                              # small hex frees the annulus for the screws
HEX_SLOP = 0.5                # socket bigger AF. Deliberate — torque is by SHAPE.
# Long, because with a through socket the ONLY cost of extra boss is a few
# grams, while the benefit is tolerance to the servo sitting lower than
# expected — which is exactly the error that broke v1 (SV_TAB_TO_HORN = 13.0
# was too GENEROUS, i.e. the real spline sits LOW). Bias the tolerance the way
# the known failure points.
HEX_BOSS_H = 28.0
# The socket is a THROUGH hole, and the disk carries a Ø12 relief above it, so
# the boss can rise out of the top and can NEVER bottom out and jack the disk
# off its floor. Bottoming was the last remaining way for an unmeasured spline
# height to wreck the assembly; a through socket deletes it. The relief doubles
# as a sight line — look down it to confirm the hex is engaged.
HEX_SOCKET_TOP = DISK_MID
RELIEF_BORE_D = 12.0

# ---------------- v2: clamp (LOCAL coords, bore bottom at z=0) --------------
# Sized to live in the base's Ø28 bore (z 51.4..64) with the hex standing proud
# above the floor. CLAMP_H is short for exactly that reason.
SPLINE_D = 5.92               # MG996R 25T major
CLAMP_BORE = 6.2              # slip on. The pinch bolt does the gripping.
CLAMP_OD = 24.0               # must clear the base's Ø28 bore
CLAMP_H = 10.0                # short: keeps the Ø24 body clear of the coupler
SLIT_W = 1.2
PINCH_X = 8.5                 # pinch-bolt offset from axis, crosses the slit
PINCH_CB_D = 6.4              # counterbore for the M3 head
PINCH_CB_H = 4.0
CENTRE_CLR = 4.0              # lets the servo's own centre screw be used too


def cyl(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    c = cylinder(radius=r, height=z1 - z0, sections=seg)
    c.apply_translation([x, y, (z0 + z1) / 2.0])
    return c


def hexa(af, z0, z1, x=0.0, y=0.0):
    """Hexagonal prism specified across flats."""
    return cyl(af / np.sqrt(3.0), z0, z1, x, y, seg=6)


def u(parts):
    return trimesh.boolean.union(list(parts), engine="manifold")


def d(a, b):
    return trimesh.boolean.difference([a, u(b)], engine="manifold")


# =============================================================== 1. the disk
def escapement_disk():
    """In place: disk axis at DISK_AX, pocket drawn at the DISCH position."""
    dx, dy = DISK_AX
    body = cyl(DISK_D / 2, DISK_Z0, DISK_Z1, dx, dy)

    cuts = [
        # the pocket — full height, this is the whole mechanism
        cyl(POCKET_D / 2, DISK_Z0 - 1, DISK_Z1 + 1, *CHUTE_AX),
        # counterbore for the coupler, from the underside up to mid-height
        cyl((BOSS_D + BOSS_FIT) / 2, DISK_Z0 - 1, DISK_MID, dx, dy),
        # relief + sight line above the coupler: the hex can overshoot into it
        cyl(RELIEF_BORE_D / 2, DISK_MID, DISK_Z1 + 1, dx, dy),
    ]
    # 4x M3 clearance, driven DOWN from the disk's TOP face into the boss
    for k in range(N_SCREWS):
        t = np.radians(45 + 90 * k)
        cuts.append(cyl(M3_CLEAR / 2, DISK_MID - 1, DISK_Z1 + 1,
                        dx + SCREW_BC / 2 * np.cos(t),
                        dy + SCREW_BC / 2 * np.sin(t)))
    return d(body, cuts)


# ============================================================ 2. the coupler
def spline_coupler():
    """In place. Located by the DISK (which rests on the floor), not by the servo."""
    dx, dy = DISK_AX
    solids = [cyl(BOSS_D / 2, COUPLER_Z0, DISK_MID, dx, dy)]
    cuts = [
        # hex socket, opening downward. Sloppy on purpose: torque is by shape.
        # It runs almost the full height because the screws are outboard of it.
        hexa(HEX_AF + HEX_SLOP, COUPLER_Z0 - 1.0, HEX_SOCKET_TOP + 1.0, dx, dy),
    ]
    for k in range(N_SCREWS):
        t = np.radians(45 + 90 * k)
        cuts.append(cyl(M3_TAP / 2, DISK_MID - SCREW_ENGAGE, DISK_MID + 1,
                        dx + SCREW_BC / 2 * np.cos(t),
                        dy + SCREW_BC / 2 * np.sin(t)))
    return d(u(solids), cuts)


# ============================================================== 3. the clamp
def spline_clamp():
    """LOCAL coords: spline bore bottom at z=0. Absolute height is set by the
    servo and deliberately does not appear anywhere in this design."""
    solids = [
        cyl(CLAMP_OD / 2, 0.0, CLAMP_H),
        hexa(HEX_AF, CLAMP_H, CLAMP_H + HEX_BOSS_H),
    ]
    cuts = [
        cyl(CLAMP_BORE / 2, -1.0, CLAMP_H),                       # onto the spline
        cyl(CENTRE_CLR / 2, -1.0, CLAMP_H + HEX_BOSS_H + 1.0),    # centre-screw path
        # radial slit, +X, from the bore out through the wall
        box(extents=[CLAMP_OD, SLIT_W, CLAMP_H + 2.0]).apply_translation(
            [CLAMP_OD / 2, 0.0, CLAMP_H / 2.0]) or None,
    ]
    cuts = [c for c in cuts if c is not None]

    # pinch bolt: axis along Y at x = PINCH_X, crossing the slit.
    zc = CLAMP_H / 2.0
    shaft = cylinder(radius=M3_CLEAR / 2, height=CLAMP_OD + 2.0, sections=48)
    shaft.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi / 2, [1, 0, 0]))
    shaft.apply_translation([PINCH_X, 0.0, zc])
    cuts.append(shaft)

    cb = cylinder(radius=PINCH_CB_D / 2, height=PINCH_CB_H, sections=48)
    cb.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi / 2, [1, 0, 0]))
    y_out = -np.sqrt((CLAMP_OD / 2) ** 2 - PINCH_X ** 2)
    cb.apply_translation([PINCH_X, y_out + PINCH_CB_H / 2, zc])
    cuts.append(cb)

    return d(u(solids), cuts)


def main():
    out = {
        "escapement_disk_v2": escapement_disk(),
        "spline_coupler_v2": spline_coupler(),
        "spline_clamp_v2": spline_clamp(),
    }
    for name, m in out.items():
        m.export(f"{name}.stl")
        e = m.extents
        print(f"{name:22s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:6.1f} mm  "
              f"{m.volume/1000:6.1f} cm3  wt={m.is_watertight}")
    print()
    print("PRINT")
    print("  escapement_disk_v2  UNDERSIDE DOWN, 10-15% gyroid, no supports.")
    print("                      ~110 g despite the 550 cm3 envelope. Flat")
    print("                      underside -> full-face first layer. Only")
    print("                      overhang is the counterbore ceiling at z=86,")
    print("                      a 7.6 mm annular bridge.")
    print("  spline_coupler_v2   boss UP (socket mouth on the plate). 4 perims,")
    print("                      40% infill, no supports. Socket prints as a")
    print("                      plain hex hole bored upward.")
    print("  spline_clamp_v2     hex UP, no supports, 4 perimeters, 50% infill.")
    print("                      Solid-ish: this part takes all the drive torque.")


if __name__ == "__main__":
    main()
