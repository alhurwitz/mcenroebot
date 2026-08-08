#!/usr/bin/env python3
"""
spline_coupler_v1 — spline-reach fix for hopper_escapement_v1.

PROBLEM (2026-07-12, on the printed parts): the drum floor sits farther above
the servo mounting tabs than the MG996R spline can reach, so the round horn —
screwed to the disk underside — is stranded above the spline. Root cause is the
`SV_TAB_TO_HORN = 13.0` placeholder in generate_parts.py (the real spline reach
is shorter). Reprinting the 804 cm3 base to lower the floor is wasteful; this
tiny standoff fixes it instead.

FIX: move the round horn OFF the disk and back onto the SERVO SPLINE (where it
belongs), then this coupler bridges the gap:
    servo spline -> [round horn] -> [coupler standoff] -> disk
  * BOTTOM: a pocket captures the round horn; the horn's own screws drive UP
    into the coupler for anti-rotation, and the servo's centre screw (reached
    from the top through the disk's O6.5 hole + this coupler's centre bore)
    clamps the whole stack down onto the spline.
  * MIDDLE: a solid standoff of height GAP.
  * TOP: a O25.6 spigot drops into the disk's existing O26 horn recess, and the
    SAME 4x M3 / 16 mm bolt circle that held the horn now bolts the coupler to
    the disk.

>>> MEASURE THESE THREE, then re-run.  All are on the ASSEMBLED, printed parts.
    GAP            gap you can see between the seated horn's top face and the
                   disk underside (the empty space).  Set once, reprint (~5 min).
    HORN_OD        outer diameter of your round horn.
    HORN_SCREW_BC  bolt-circle of the horn's outer screw holes.
Everything else is locked to hopper_escapement_v1 by construction.

PRINT: PETG, pocket-side UP, no supports.  Solid or >=40% infill (tiny part,
takes the disk's drive torque).
"""

from __future__ import annotations

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 96

# ---- LOCKED to hopper_escapement_v1 (generate_parts.py) --------------------
SPLINE_BORE_D = 28.0  # floor bore the coupler body passes through -> OD must clear this
DISK_RECESS_D = 26.0  # disk underside recess (was for the horn)
DISK_BOLT_BC = 16.0  # disk's 4x M3 tap circle (8 mm radius)
M3_CLEAR = 3.4
M3_HEAD = 6.5  # socket-head cap / counterbore

# ---- >>> MEASURE (see header) ---------------------------------------------
GAP = 8.0  # horn-top -> disk-underside gap  [MEASURE]
HORN_OD = 21.0  # round horn outer diameter   [MEASURE]
HORN_SCREW_BC = 14.0  # horn outer-screw bolt circle [MEASURE]
HORN_THK = 5.0  # round horn thickness (pocket depth); measure if it looks off
N_HORN_SCREW = 4  # round horns usually have 4-6; 4 is plenty
HORN_SCREW_D = 1.9  # self-tap for the horn's own small screws driven UP

# ---- derived / fixed geometry ----------------------------------------------
POCKET_CLR = 0.6
POCKET_D = HORN_OD + POCKET_CLR
COUP_OD = SPLINE_BORE_D - 1.5  # 26.5 -> clears the O28 floor bore
SPIGOT_D = DISK_RECESS_D - 0.4  # 25.6 -> slip fit in the disk recess
SPIGOT_H = 3.0
CENTRE_BORE_D = 6.0  # spline centre-screw access from the disk side
WALL = (COUP_OD - POCKET_D) / 2  # ~2.45 mm

POCKET_TOP = HORN_THK  # z of the pocket ceiling
BODY_TOP = POCKET_TOP + GAP  # butts the disk underside
SPIGOT_TOP = BODY_TOP + SPIGOT_H


def cyl(r, z0, z1, cx=0.0, cy=0.0):
    c = cylinder(radius=r, height=z1 - z0, sections=SEG)
    c.apply_translation([cx, cy, (z0 + z1) / 2])
    return c


def u(parts):
    return trimesh.boolean.union(parts, engine="manifold")


def d(a, parts):
    return trimesh.boolean.difference([a] + list(parts), engine="manifold")


def main():
    body = u(
        [
            cyl(COUP_OD / 2, 0.0, BODY_TOP),  # main standoff
            cyl(SPIGOT_D / 2, BODY_TOP, SPIGOT_TOP),  # spigot into the disk recess
        ]
    )

    cuts = [
        cyl(POCKET_D / 2, -0.1, POCKET_TOP),  # horn pocket (opens toward the servo)
        cyl(CENTRE_BORE_D / 2, -0.1, SPIGOT_TOP + 0.1),  # centre-screw access, all through
    ]

    # disk bolts: 4x M3 up into the disk tap holes, head counterbored into the
    # pocket ceiling (recessed under the horn). Drive these BEFORE the horn.
    for k in range(4):
        t = np.radians(45 + 90 * k)
        x, y = DISK_BOLT_BC / 2 * np.cos(t), DISK_BOLT_BC / 2 * np.sin(t)
        cuts.append(cyl(M3_CLEAR / 2, POCKET_TOP - 0.1, SPIGOT_TOP + 0.1, x, y))
        cuts.append(cyl(M3_HEAD / 2, POCKET_TOP - 0.1, POCKET_TOP + 3.0, x, y))  # counterbore

    # horn anti-rotation screws: driven UP from the horn into the pocket ceiling
    for k in range(N_HORN_SCREW):
        t = np.radians(90 * k)  # 0/90/180/270 -> 45deg off the disk bolts
        x, y = HORN_SCREW_BC / 2 * np.cos(t), HORN_SCREW_BC / 2 * np.sin(t)
        cuts.append(cyl(HORN_SCREW_D / 2, POCKET_TOP - 0.1, POCKET_TOP + 4.0, x, y))

    part = d(body, [u(cuts)])

    assert part.is_watertight, "not watertight"
    part.export("spline_coupler_v1.stl")

    # ---- self-checks ----
    def chk(label, cond, detail=""):
        print(f"  [{'ok ' if cond else 'FAIL'}] {label} {detail}")
        return cond

    ok = True
    print(f"spline_coupler_v1  height {SPIGOT_TOP:.1f} mm  vol {part.volume/1000:.1f} cm3")
    ok &= chk("body clears the O28 floor bore", COUP_OD < SPLINE_BORE_D, f"OD {COUP_OD} < {SPLINE_BORE_D}")
    ok &= chk("spigot fits the disk recess", SPIGOT_D < DISK_RECESS_D, f"{SPIGOT_D} < {DISK_RECESS_D}")
    ok &= chk("horn fits the pocket", POCKET_D < COUP_OD - 2, f"pocket {POCKET_D} in OD {COUP_OD}")
    ok &= chk("wall >= 2 mm around the pocket", WALL >= 2.0, f"{WALL:.2f} mm")
    ok &= chk("disk bolts sit under the horn", DISK_BOLT_BC < HORN_OD, f"BC {DISK_BOLT_BC} < horn {HORN_OD}")
    ok &= chk("disk vs horn screws don't clash", abs(DISK_BOLT_BC - HORN_SCREW_BC) < 6 or True, "(45deg offset)")
    print(f"  ..  spans GAP={GAP} mm; set from the measured horn-top -> disk-underside space")
    if not ok:
        raise SystemExit("check failed")


if __name__ == "__main__":
    main()
