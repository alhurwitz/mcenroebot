#!/usr/bin/env python3
"""
drive_rod_v1 (horn-free re-cut, 2026-07-25) — drive bridge, spline -> disk.
NO HORN.

History: v1 socket was modeled O5.5 -> too tight to even press onto the ~O5.9
spline.  The horn-capture detour meant drilling the horn (bad call).  This
version drops the horn entirely and does what AJ asked: a rod that clamps the
SPLINE directly and bolts to the DISK.

  * BOTTOM: a O6.2 socket that SLIPS over the spline (loose on purpose), locked
    by a RADIAL M3 GRUB SCREW that bites between the spline teeth.  The grub
    carries the torque, so the printed bore doesn't need to grip — that's what
    killed the first one.  Optional M3 down the centre into the spline's centre
    hole for axial hold.
  * MIDDLE: O13 shaft, height SPAN.
  * TOP: O24 flange, 4x M3 up into the disk's existing 16 mm tap holes.

>>> KNOBS:
    SPAN       spline-tip -> disk-underside gap. THE length knob — print, tell
               me longer/shorter.
    SOCKET_D   6.2 default. If it presses on too tight, bump up; the grub does
               the gripping, so err LOOSE.  (Modeled holes print a few tenths
               under, which is why 5.5 jammed.)

ASSEMBLE (disk-first, so the flange bolts are reachable):
  1. Bolt the rod flange UP into the disk (4x M3 into the disk taps).  Disk +
     rod are now one unit; heads sit under the flange, open to a driver.
  2. Park the servo at LOAD (~15 deg).
  3. Lower the disk+rod onto the servo so the socket slips over the spline and
     the disk lands flat on the floor, pocket under the cone outlet.
  4. Tighten the radial grub screw onto the spline. (+ optional centre screw.)

PRINT: PETG, flange UP (socket on the bed), no supports.  Solid / >=50% infill.
"""

from __future__ import annotations

import numpy as np
import trimesh
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix

SEG = 96

# ---- LOCKED to hopper_escapement_v1 ----
FLOOR_BORE_D = 28.0
DISK_BC = 16.0
M3_CLEAR = 3.4
M3_HEAD = 6.5

# ---- >>> KNOBS ----
SPAN = 8.0  # spline tip -> disk underside   [ITERATE]
SOCKET_D = 6.0  # slip over the ~5.9 spline    [tune LOOSE]
SPLINE_ENGAGE = 6.0  # socket depth over the spline
GRUB_TAP_D = 2.6  # radial M3 self-tap set screw

# ---- fixed geometry ----
SHAFT_OD = 13.0
FLANGE_OD = 24.0  # < floor bore 28
FLANGE_T = 5.0
CENTRE_D = 3.5  # optional axial retention screw into the spline centre

FLANGE_Z0 = SPLINE_ENGAGE + SPAN
FLANGE_Z1 = FLANGE_Z0 + FLANGE_T


def cyl(r, z0, z1, cx=0.0, cy=0.0, axis="z"):
    c = cylinder(radius=r, height=z1 - z0, sections=SEG)
    if axis == "x":
        c.apply_transform(rotation_matrix(np.pi / 2, [0, 1, 0]))
        c.apply_translation([(z0 + z1) / 2, cy, cx])
    else:
        c.apply_translation([cx, cy, (z0 + z1) / 2])
    return c


def u(p):
    return trimesh.boolean.union(p, engine="manifold")


def d(a, p):
    return trimesh.boolean.difference([a] + list(p), engine="manifold")


def main():
    body = u([cyl(SHAFT_OD / 2, 0, FLANGE_Z0), cyl(FLANGE_OD / 2, FLANGE_Z0, FLANGE_Z1)])

    cuts = [
        cyl(SOCKET_D / 2, -0.1, SPLINE_ENGAGE),  # spline socket
        cyl(CENTRE_D / 2, SPLINE_ENGAGE, FLANGE_Z1 + 0.1),  # optional centre screw
        cyl(GRUB_TAP_D / 2, SHAFT_OD / 2 + 0.1, 0.0, cx=SPLINE_ENGAGE / 2, axis="x"),  # radial grub
    ]
    for k in range(4):  # flange -> disk taps
        t = np.radians(45 + 90 * k)
        x, y = DISK_BC / 2 * np.cos(t), DISK_BC / 2 * np.sin(t)
        cuts.append(cyl(M3_CLEAR / 2, FLANGE_Z0 - 0.1, FLANGE_Z1 + 0.1, x, y))
        cuts.append(cyl(M3_HEAD / 2, FLANGE_Z0 - 0.1, FLANGE_Z0 + 2.5, x, y))  # head clearance

    part = d(body, [u(cuts)])
    assert part.is_watertight, "not watertight"
    part.export("drive_rod_v1.stl")

    ok = True

    def chk(label, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok ' if cond else 'FAIL'}] {label} {detail}")

    print(f"drive_rod_v1 (horn-free)  length {FLANGE_Z1:.1f}  vol {part.volume/1000:.1f} cm3")
    chk("flange clears floor bore", FLANGE_OD < FLOOR_BORE_D, f"{FLANGE_OD} < {FLOOR_BORE_D}")
    chk("socket slips on the spline", SOCKET_D >= 5.9, f"O{SOCKET_D} ~ spline ~5.9")
    chk("grub wall", (SHAFT_OD - SOCKET_D) / 2 >= 3.0, f"{(SHAFT_OD - SOCKET_D)/2:.2f} mm")
    chk("bolts fit the flange", DISK_BC + M3_HEAD < FLANGE_OD, f"BC16 + head in O{FLANGE_OD}")
    print(f"  ..  SPAN={SPAN} mm is the length knob; grub screw carries the torque (no horn)")
    if not ok:
        raise SystemExit("check failed")


if __name__ == "__main__":
    main()
