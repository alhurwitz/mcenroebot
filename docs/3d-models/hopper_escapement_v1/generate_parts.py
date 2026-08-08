#!/usr/bin/env python3
"""
hopper_escapement_v1 — integrated cone hopper + rotary escapement disk, bolted
DIRECTLY onto the launcher's drop-chute flange.

WHY (AJ, 2026-07-12): kills the scoop-arm feed unit (`feed_unit_v1` +
`feed_servo_wall_v2` + `scoop_arm_cup26_v3`) and the whole telescoping
`feed_launcher_coupler_v1` chain. Those stood beside the launcher on a long
swinging arm and needed a catch funnel to bridge the gap. This is one bolt-on
tower: cone -> disk -> chute, no arm, no coupler, no free-flight ball.

MECHANISM — rotary pocket disk (the classic ball-machine escapement, and the
revival of the shelved archive/F1_escapement_disk idea):
  * A Ø136 x 44 disk with ONE Ø44 through-pocket rides on a flat floor plate.
  * At LOAD the pocket sits under the cone's Ø46 outlet; a ball drops in and
    rests on the FLOOR (the disk is a through-hole carrier, not a cup).
  * The disk sweeps 150 deg. Everywhere except the two holes the floor blocks
    the ball below and the lid blocks the stack above.
  * At DISCH the pocket lands over the Ø46 floor hole — dead on the launcher's
    chute axis — and the ball drops straight down the chute.
  * One MG996R (ch5, POSITIONAL) direct-drives the disk. Two commanded angles,
    exactly like scripts/triwheel_spin_test.py already does:
        LOAD_ANGLE  ~15 deg      DISCH_ANGLE ~165 deg      (150 deg sweep)
    Retune on the bench; ±5 deg of servo error still drops the ball (a Ø40 ball
    clears the Ø46 hole / Ø44 pocket overlap up to ~5 mm of offset).

GEOMETRY / FRAME (mm) — same axes as launcher_bracket_v4_tri, origin moved to
the chute axis on the TOP FACE of the bracket's coupler flange:
    launcher (x, y, z) = (X - 60, Y + 49, Z + 156)
  +X = fire direction, +Z up. The whole hopper therefore lives at -X (behind
  the wheels), which is also where the auger already stands.

  chute axis   (0, 0)      DISCH hole, Ø46, straight into the bracket's 44-sq chute
  disk axis    (-40, 0)    servo spline; pocket orbit radius R_P = 40
  cone axis    (-74.6, 20) LOAD hole, 150 deg round from DISCH

  The 20 mm lateral (Y) throat offset is deliberate: it buys a 150 deg servo
  sweep instead of a full 180 deg (no clone-range gamble), and a Y offset costs
  nothing — the tilt axis IS Y (no gravity moment) and pan is vertical.

PARTS (5 prints, PETG):
  1 hopper_base_v1     flange + 45 deg self-supporting flare + drum floor/wall
                       + servo cavity.  Print flange-down. No supports.
  2 escapement_disk_v1 the circle piece.  Print flat.  10-15% gyroid.
  3 servo_saddle_v1    MG996R cradle; servo bolts to it OFF the machine, then
                       the pair lifts up into the cavity from below.
  4 drum_lid_v1        ceiling over the disk; carries the cone.  Print flat.
  5 hopper_cone_v1     Ø200 rim -> Ø46 throat, 60 deg walls, ~20 balls.
                       Print RIM-DOWN (inverted): 60 deg walls = 30 deg from
                       vertical, no supports.

ASSEMBLY ORDER (matters — some fasteners are captive):
  a. Heat-set M3 inserts: 4 in the drum-wall top (lid), 2 in the servo-cavity
     ceiling (saddle), 4 in the saddle itself may be self-tapped instead.
  b. Bolt the servo to the saddle (tabs on the saddle's TOP face, body down
     through the window).  c. Screw the horn into the disk's underside recess
     (4x M3 through the horn — drill the horn's holes out to 3.2).
  d. Drop the disk into the drum, pocket down.  e. Lift the saddle+servo up
     into the cavity from below, engage the spline into the horn, 2x M3 up into
     the ceiling inserts.  f. Lid on, 4x M3.  g. Cone on, 4x M3.
  h. THEN bolt the whole tower to the launcher (4x M3, 70 mm square) — the
     servo cable exits down through the cavity, past the flange's rear edge.

PLACEHOLDERS / GATES (do these before printing the base):
  * CALIPER THE MG996R.  Published pattern used here: body 40.7 x 19.7,
    spline 10.0 mm behind the front face, tab holes 49.5 (long) x 10 (short).
    docs/mg996r_fit_precheck.md says clones vary ~1.5 mm — the saddle is the
    cheap reprint, so measure and fix SADDLE constants only.
  * SERVO_TAB_TO_HORN (13.0) is a guess: tab plane -> horn seating face.
    It only sets how hard the disk is pressed onto the floor; shim the saddle
    with M3 washers to leave the disk just kissing the floor.
  * The bracket's flange bolt pattern is itself a v3 placeholder
    (FLANGE_BOLT_HALF = 35).  Matched here BY CONSTRUCTION — if it moves there,
    change FLANGE_BOLT_HALF here too.
  * CG: this puts ~650 g of plastic + 20 balls ~270 mm above the chute flange
    and ~75 mm behind it.  Revisit the shooter_stand_v2 counterweight.
"""

from __future__ import annotations

import numpy as np
import trimesh
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix

SEG = 96

# ---------------------------------------------------------------- ball / stock
BALL = 40.0
M3_CLEAR = 3.4
M3_TAP = 3.2
INSERT_D = 4.2  # M3 heat-set
INSERT_H = 6.0

# ------------------------------------------------- launcher interface (LOCKED)
# launcher_bracket_v4_tri: chute 44 sq, coupler flange 90x90, 4x M3 on a 70 sq.
FLANGE_BOLT_HALF = 35.0
BORE_D = 46.0  # round drop bore (ball 40 -> 3 mm clearance)
BORE_R = BORE_D / 2

# ------------------------------------------------------------------ escapement
R_P = 40.0  # pocket orbit radius = disk-axis -> hole centers
SWEEP_DEG = 150.0  # LOAD is this far round from DISCH
DISK_D = 136.0
DISK_T = 44.0  # >= ball, so the stack never sees the pocket sideways
POCKET_D = 44.0
DISK_GAP = 0.4  # disk underside float over the floor
WALL_CLR = 0.75  # drum wall -> disk edge (the wall IS the journal)
CEIL_GAP = 1.0  # lid underside -> disk top (too small for a ball to enter)

DISK_AX = np.array([-R_P, 0.0])
CHUTE_AX = np.array([0.0, 0.0])
_t = np.radians(SWEEP_DEG)
CONE_AX = DISK_AX + R_P * np.array([np.cos(_t), np.sin(_t)])  # (-74.64, +20.0)

# ------------------------------------------------------------------- z stack-up
FLG_T = 6.0  # base flange 0..6
FLARE_FOOT_R = 30.0  # 45 deg cones start here at z = FLG_T
FLOOR_Z0, FLOOR_Z1 = 58.0, 64.0  # drum floor
DISK_Z0 = FLOOR_Z1 + DISK_GAP  # 64.4
DISK_Z1 = DISK_Z0 + DISK_T  # 108.4
LID_Z0 = DISK_Z1 + CEIL_GAP  # 109.4
LID_T = 6.0
LID_Z1 = LID_Z0 + LID_T  # 115.4

DRUM_R = 78.0  # drum OD 156 (9.25 wall -> takes an M3 insert)
DRUM_IR = DISK_D / 2 + WALL_CLR  # 68.75
LID_BOLT_R = 73.4  # mid-wall
LID_BOLT_ANG = (0.0, 90.0, 180.0, 270.0)  # NOT 45s — 135 would foul the cone flange

# ---------------------------------------------------------------- servo MG996R
SV_L, SV_W = 40.7, 19.7  # body: long axis along +Y, short along X
SV_SPLINE_FROM_FACE = 10.0  # spline -> front body face
SV_TAB_LONG, SV_TAB_SHORT = 49.5, 10.0  # tab hole pattern
SV_BODY_DROP = 27.0  # tab plane -> bottom of case
SV_TAB_TO_HORN = 13.0  # tab plane -> horn seating face  [SHIM WITH WASHERS]

SV_BC_Y = SV_L / 2 - SV_SPLINE_FROM_FACE  # +10.35 body centre, spline at y=0
TAB_PLANE = DISK_Z0 - SV_TAB_TO_HORN  # 51.4  (saddle TOP face)
SADDLE_T = 6.0
SADDLE_Z0 = TAB_PLANE - SADDLE_T
SPLINE_BORE_D = 28.0  # clears the servo boss + the horn

# servo cavity (a prism cut up through the flare, open at the bottom)
CAV_X0, CAV_X1 = -56.5, -26.0  # x1 keeps >=3 mm of meat to the Ø46 bore
CAV_Y0, CAV_Y1 = -25.5, 46.5
SADDLE_X0, SADDLE_X1 = CAV_X0 + 0.5, CAV_X1 - 0.5
SADDLE_Y0, SADDLE_Y1 = CAV_Y0 + 0.5, CAV_Y1 - 0.5
EAR = ((-R_P, -21.0), (-R_P, 42.0))  # saddle -> cavity-ceiling screws

# base flange footprint (reaches back far enough to root the flare)
FX0, FX1 = -70.0, 45.0
FY0, FY1 = -45.0, 45.0

# ------------------------------------------------------------------ hopper cone
CONE_RIM_D = 200.0
CONE_WALL_DEG = 60.0  # from horizontal; stays >=30 deg even at 30 deg turret tilt
CONE_WALL_T = 3.0
CONE_THROAT_H = 12.0  # straight collar above the flange
CONE_FLG_D = 72.0
CONE_FLG_BC = 58.0
CONE_FLG_T = 6.0
CONE_LIP = 4.0


# ---------------------------------------------------------------------- helpers
def B(x0, x1, y0, y1, z0, z1):
    b = box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def cyl(r, z0, z1, cx=0.0, cy=0.0):
    c = cylinder(radius=r, height=z1 - z0, sections=SEG)
    c.apply_translation([cx, cy, (z0 + z1) / 2])
    return c


def frustum(r0, z0, r1, z1, cx=0.0, cy=0.0):
    """Exact truncated cone as the convex hull of two circles (both convex)."""
    a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    pts = np.vstack(
        [
            np.column_stack([cx + r0 * np.cos(a), cy + r0 * np.sin(a), np.full(SEG, z0)]),
            np.column_stack([cx + r1 * np.cos(a), cy + r1 * np.sin(a), np.full(SEG, z1)]),
        ]
    )
    return trimesh.PointCloud(pts).convex_hull


def u(parts):
    return trimesh.boolean.union(parts, engine="manifold")


def d(a, parts):
    return trimesh.boolean.difference([a] + list(parts), engine="manifold")


def i(parts):
    return trimesh.boolean.intersection(parts, engine="manifold")


# ------------------------------------------------------------------ 1. the base
def hopper_base():
    dx, dy = DISK_AX

    solids = [B(FX0, FX1, FY0, FY1, 0, FLG_T)]

    # 45 deg flare: TWO cones (one on each axis) so the union covers the whole
    # drum footprint with nothing shallower than 45 deg -> support-free.
    top_r = FLARE_FOOT_R + (FLOOR_Z0 - FLG_T)  # 82 @ z=58
    flare = u(
        [
            frustum(FLARE_FOOT_R, FLG_T, top_r, FLOOR_Z0, 0.0, 0.0),
            frustum(FLARE_FOOT_R, FLG_T, top_r, FLOOR_Z0, dx, dy),
        ]
    )
    # trim to the drum footprint (a vertical cut -> still printable)
    flare = i([flare, cyl(DRUM_R, FLG_T - 1, FLOOR_Z0 + 1, dx, dy)])
    solids.append(flare)

    solids.append(cyl(DRUM_R, FLOOR_Z0, FLOOR_Z1, dx, dy))  # drum floor
    solids.append(  # drum wall
        d(cyl(DRUM_R, FLOOR_Z1, LID_Z0, dx, dy), [cyl(DRUM_IR, FLOOR_Z1 - 1, LID_Z0 + 1, dx, dy)])
    )

    part = u(solids)

    cuts = []
    # drop bore, all the way through, + lead-in chamfer at the floor face
    cuts.append(cyl(BORE_R, -1, FLOOR_Z1 + 1))
    cuts.append(frustum(BORE_R + 3, FLOOR_Z1, BORE_R, FLOOR_Z1 - 3))
    # launcher bolts
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(
                cyl(M3_CLEAR / 2, -1, FLG_T + 1, sx * FLANGE_BOLT_HALF, sy * FLANGE_BOLT_HALF)
            )
    # servo cavity (open at the bottom: insertion + cable exit)
    cuts.append(B(CAV_X0, CAV_X1, CAV_Y0, CAV_Y1, -1, TAB_PLANE))
    # spline / horn bore up into the drum
    cuts.append(cyl(SPLINE_BORE_D / 2, TAB_PLANE - 1, FLOOR_Z1 + 1, dx, dy))
    # saddle screw inserts in the cavity ceiling
    for ex, ey in EAR:
        cuts.append(cyl(INSERT_D / 2, TAB_PLANE, TAB_PLANE + INSERT_H, ex, ey))
    # lid inserts in the drum-wall top
    for a in LID_BOLT_ANG:
        t = np.radians(a)
        cuts.append(
            cyl(
                INSERT_D / 2,
                LID_Z0 - 8.0,
                LID_Z0 + 1,
                dx + LID_BOLT_R * np.cos(t),
                dy + LID_BOLT_R * np.sin(t),
            )
        )
    return d(part, [u(cuts)])


# ------------------------------------------------------------------ 2. the disk
def escapement_disk():
    """Modelled in place (disk axis at DISK_AX, pocket at the DISCH position)."""
    dx, dy = DISK_AX
    disk = cyl(DISK_D / 2, DISK_Z0, DISK_Z1, dx, dy)
    cuts = [
        cyl(POCKET_D / 2, DISK_Z0 - 1, DISK_Z1 + 1, *CHUTE_AX),  # the pocket
        cyl(26.0 / 2, DISK_Z0 - 1, DISK_Z0 + 3.5, dx, dy),  # horn recess
        cyl(6.5 / 2, DISK_Z0 - 1, DISK_Z1 + 1, dx, dy),  # horn-screw access
    ]
    for k in range(4):  # 4x M3 into the horn, 16 mm BC
        t = np.radians(45 + 90 * k)
        cuts.append(
            cyl(M3_TAP / 2, DISK_Z0 - 1, DISK_Z0 + 11, dx + 8 * np.cos(t), dy + 8 * np.sin(t))
        )
    return d(disk, [u(cuts)])


# ---------------------------------------------------------------- 3. the saddle
def servo_saddle():
    plate = B(SADDLE_X0, SADDLE_X1, SADDLE_Y0, SADDLE_Y1, SADDLE_Z0, TAB_PLANE)
    cuts = [  # body window (body hangs through it, tabs land on the top face)
        B(
            DISK_AX[0] - SV_W / 2 - 0.5,
            DISK_AX[0] + SV_W / 2 + 0.5,
            SV_BC_Y - SV_L / 2 - 0.6,
            SV_BC_Y + SV_L / 2 + 0.6,
            SADDLE_Z0 - 1,
            TAB_PLANE + 1,
        )
    ]
    for sx in (-1, 1):  # servo tab screws (self-tap M3)
        for sy in (-1, 1):
            cuts.append(
                cyl(
                    M3_TAP / 2,
                    SADDLE_Z0 - 1,
                    TAB_PLANE + 1,
                    DISK_AX[0] + sx * SV_TAB_SHORT / 2,
                    SV_BC_Y + sy * SV_TAB_LONG / 2,
                )
            )
    for ex, ey in EAR:  # up into the cavity ceiling
        cuts.append(cyl(M3_CLEAR / 2, SADDLE_Z0 - 1, TAB_PLANE + 1, ex, ey))
    return d(plate, [u(cuts)])


# ------------------------------------------------------------------- 4. the lid
def drum_lid():
    dx, dy = DISK_AX
    lid = cyl(DRUM_R, LID_Z0, LID_Z1, dx, dy)
    cuts = [
        cyl(BORE_R, LID_Z0 - 1, LID_Z1 + 1, *CONE_AX),  # LOAD hole
        frustum(BORE_R + 3, LID_Z1, BORE_R, LID_Z1 - 3, *CONE_AX),  # lead-in
    ]
    for a in LID_BOLT_ANG:  # down into the drum wall
        t = np.radians(a)
        cuts.append(
            cyl(
                M3_CLEAR / 2,
                LID_Z0 - 1,
                LID_Z1 + 1,
                dx + LID_BOLT_R * np.cos(t),
                dy + LID_BOLT_R * np.sin(t),
            )
        )
    for k in range(4):  # cone flange
        t = np.radians(45 + 90 * k)
        cuts.append(
            cyl(
                M3_CLEAR / 2,
                LID_Z0 - 1,
                LID_Z1 + 1,
                CONE_AX[0] + CONE_FLG_BC / 2 * np.cos(t),
                CONE_AX[1] + CONE_FLG_BC / 2 * np.sin(t),
            )
        )
    return d(lid, [u(cuts)])


# ------------------------------------------------------------------ 5. the cone
def hopper_cone():
    """Built in place, standing on the lid at CONE_AX."""
    cx, cy = CONE_AX
    z0 = LID_Z1
    z1 = z0 + CONE_FLG_T
    z2 = z1 + CONE_THROAT_H
    rise = (CONE_RIM_D / 2 - BORE_R) * np.tan(np.radians(CONE_WALL_DEG))
    z3 = z2 + rise

    solids = [
        cyl(CONE_FLG_D / 2, z0, z1, cx, cy),  # flange
        frustum(CONE_FLG_D / 2, z1, BORE_R + CONE_WALL_T, z1 + 9.0, cx, cy),  # 45 chamfer
        cyl(BORE_R + CONE_WALL_T, z1, z2, cx, cy),  # throat collar
        frustum(BORE_R + CONE_WALL_T, z2, CONE_RIM_D / 2 + CONE_WALL_T, z3, cx, cy),  # flare
        cyl(CONE_RIM_D / 2 + CONE_WALL_T + 2, z3, z3 + CONE_LIP, cx, cy),  # rim lip
    ]
    body = u(solids)

    cuts = [
        cyl(BORE_R, z0 - 1, z2 + 0.1, cx, cy),  # throat bore
        frustum(BORE_R, z2, CONE_RIM_D / 2, z3, cx, cy),  # cone cavity
        cyl(CONE_RIM_D / 2, z3 - 0.1, z3 + CONE_LIP + 1, cx, cy),  # through the lip
    ]
    for k in range(4):
        t = np.radians(45 + 90 * k)
        cuts.append(
            cyl(
                M3_CLEAR / 2,
                z0 - 1,
                z1 + 1,
                cx + CONE_FLG_BC / 2 * np.cos(t),
                cy + CONE_FLG_BC / 2 * np.sin(t),
            )
        )
    return d(body, [u(cuts)]), z3 + CONE_LIP


# ----------------------------------------------------------------------- checks
def checks(rim_z):
    ok = True

    def chk(label, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok ' if cond else 'FAIL'}] {label} {detail}")

    print("geometry self-checks")
    sep = np.linalg.norm(CONE_AX - CHUTE_AX)
    chk("LOAD/DISCH hole separation", sep > BORE_D + 6, f"{sep:.1f} > {BORE_D + 6:.0f}")
    chk("holes sit over the disk", R_P + BORE_R < DRUM_IR, f"{R_P + BORE_R:.1f} < {DRUM_IR:.2f}")
    chk("pocket land at disk edge", DISK_D / 2 - (R_P + POCKET_D / 2) >= 5, f"{DISK_D / 2 - (R_P + POCKET_D / 2):.1f} mm")
    chk("ball fully inside pocket", DISK_T >= BALL + 3, f"disk {DISK_T} vs ball {BALL}")
    chk("ceiling gap blocks a ball", CEIL_GAP < 5, f"{CEIL_GAP} mm")
    # servo body vs the Ø46 drop bore
    chk("servo cavity clears bore", abs(CAV_X1) - BORE_R >= 3.0, f"{abs(CAV_X1) - BORE_R:.1f} mm of meat")
    # cone flange vs the nearest lid bolt (the 180 deg one)
    b180 = DISK_AX + LID_BOLT_R * np.array([-1.0, 0.0])
    gap = np.linalg.norm(b180 - CONE_AX) - CONE_FLG_D / 2
    chk("lid bolt clears cone flange", gap > 3, f"{gap:.1f} mm")
    # capacity
    h = (CONE_RIM_D / 2 - BORE_R) * np.tan(np.radians(CONE_WALL_DEG))
    R, r = CONE_RIM_D / 2, BORE_R
    vol = np.pi * h / 3 * (R * R + R * r + r * r) / 1000  # cm3
    balls = vol * 0.62 / (4 / 3 * np.pi * (BALL / 2) ** 3 / 1000)
    chk("capacity >= 18 balls", balls >= 18, f"~{balls:.0f} balls ({vol:.0f} cm3)")
    chk("cone fits a 256 bed", CONE_RIM_D + 2 * CONE_WALL_T + 4 < 256, f"Ø{CONE_RIM_D + 2 * CONE_WALL_T + 4:.0f}")
    print(f"  ..  servo sweep {SWEEP_DEG:.0f} deg -> LOAD_ANGLE ~15, DISCH_ANGLE ~165 (ch5)")
    print(f"  ..  cone axis  {CONE_AX.round(1).tolist()}   rim top z={rim_z:.0f}")
    print(f"  ..  launcher frame: rim {rim_z + 156:.0f} mm above the bracket plate")
    return ok


def main():
    base = hopper_base()
    disk = escapement_disk()
    saddle = servo_saddle()
    lid = drum_lid()
    cone, rim_z = hopper_cone()

    parts = {
        "hopper_base_v1": base,
        "escapement_disk_v1": disk,
        "servo_saddle_v1": saddle,
        "drum_lid_v1": lid,
        "hopper_cone_v1": cone,
    }
    for name, m in parts.items():
        assert m.is_watertight, f"{name} not watertight"
        m.export(f"{name}.stl")
        print(
            f"{name:20s} watertight={m.is_watertight} "
            f"vol={m.volume / 1000:7.1f} cm3  bounds={m.bounds.round(0).tolist()}"
        )

    # in-place assembly (for inspection / collision checks in a slicer)
    trimesh.util.concatenate(list(parts.values())).export("hopper_escapement_v1.stl")
    print("hopper_escapement_v1.stl  = all 5 parts in assembled position\n")

    if not checks(rim_z):
        raise SystemExit("geometry check failed")


if __name__ == "__main__":
    main()
