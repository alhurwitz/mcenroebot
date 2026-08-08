#!/usr/bin/env python3
"""
saddle_standoff_v1 — downward mounting posts for the servo saddle (no inserts).

AJ wants to bolt the saddle on FROM BELOW (easy — the cavity is open at the
bottom) instead of blind-bolting up into ceiling inserts he doesn't have. These
posts do that:
    glue the peg UP into a ceiling O4.2 hole -> a O7 post hangs DOWN by DROP ->
    the saddle ear bolts to the post's bottom face with one M3 (up from below).

Two posts (the saddle's two ear positions) locate the servo and stop it turning.

>>> DROP is the knob.  Print a pair, offer the saddle up, and tell me if they
    need to be longer or shorter; I re-run with a new DROP in seconds.  DROP is
    just how far below the ceiling the servo hangs — pick whatever gives comfy
    finger room to drive the two ear screws; smaller is better for spline reach.

COUPLING TO THE DRIVE BRIDGE (read this):
  DROP sets how far the servo drops, which sets how far the spline sits below
  the disk, which sets the length of the drive bridge (drive_rod_v1 / coupler).
  So: lock DROP FIRST (get the servo mounted solid), THEN we size the bridge to
  match.  One variable at a time.

PRINT: PETG, peg UP, no supports.  Solid.  Glue the peg in with CA/epoxy.
"""

from __future__ import annotations

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 64

HOLE_D = 4.2  # ceiling insert holes
PEG_D = 4.1  # glue slip-fit into the ceiling hole
PEG_H = 6.0  # ceiling hole is ~6 deep
POST_D = 7.0  # hangs below the ceiling; > hole so it stops flush at the ceiling
PILOT_D = 2.6  # M3 self-tap for the saddle ear screw
PILOT_DEPTH = 8.0

DROP = 6.0  # <<< THE KNOB: servo hang below the ceiling  [print, tell me longer/shorter]

EAR_PITCH = 63.0  # saddle ear spacing (EAR (-40,-21) -> (-40,42)); for the pair layout


def cyl(r, z0, z1, cx=0.0, cy=0.0):
    c = cylinder(radius=r, height=z1 - z0, sections=SEG)
    c.apply_translation([cx, cy, (z0 + z1) / 2])
    return c


def one(cx=0.0, cy=0.0):
    # z=0 = bottom (saddle bolts here); peg on top goes into the ceiling
    body = trimesh.boolean.union(
        [cyl(POST_D / 2, 0.0, DROP, cx, cy), cyl(PEG_D / 2, DROP, DROP + PEG_H, cx, cy)],
        engine="manifold",
    )
    pilot = cyl(PILOT_D / 2, -0.1, PILOT_DEPTH, cx, cy)
    return trimesh.boolean.difference([body, pilot], engine="manifold")


def main():
    post = one()
    assert post.is_watertight, "not watertight"
    post.export("saddle_standoff_v1.stl")

    pair = trimesh.util.concatenate([one(0, 0), one(0, EAR_PITCH)])
    pair.export("saddle_standoff_v1_x2.stl")

    print(f"saddle_standoff_v1  DROP={DROP}  post O{POST_D}  peg O{PEG_D}x{PEG_H}  vol {post.volume/1000:.2f} cm3")
    print(f"  [{'ok ' if PEG_D < HOLE_D else 'FAIL'}] peg glue-fit O{PEG_D} < ceiling hole O{HOLE_D}")
    print(f"  [{'ok ' if POST_D > HOLE_D else 'FAIL'}] post shoulders on the ceiling O{POST_D} > O{HOLE_D}")
    print(f"  [{'ok ' if (POST_D-PILOT_D)/2 >= 2.0 else 'FAIL'}] pilot wall {(POST_D-PILOT_D)/2:.2f} mm")
    print(f"  ..  servo drops {DROP} mm below the ceiling -> drive bridge grows by ~{DROP} mm vs the estimate")


if __name__ == "__main__":
    main()
