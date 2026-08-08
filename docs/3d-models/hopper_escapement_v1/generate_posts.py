#!/usr/bin/env python3
"""
saddle_post_v1 — printed glue-in plugs that replace the heat-set inserts.

hopper_escapement_v1's base has SIX O4.2 insert holes (2 in the servo-cavity
ceiling for the saddle, 4 in the drum-wall top for the lid). With no heat-set
inserts on hand, these plugs stand in: a O4.1 dowel that glues FLUSH into each
O4.2 hole and carries an M3 self-tapping bore. Because they sit flush, nothing
about the assembly geometry changes — the saddle and lid bolt on exactly as the
original design intended, the M3 just threads into the plug instead of an insert.

USE:  print 6 (2 for the saddle, 4 for the lid).  Put a drop of CA/epoxy in the
hole, push a plug in flush (pilot bore facing OUT toward the mating part), let
it set, then drive the M3 as normal.  The thin dowel wall is backed by the hole
wall + glue, so the self-tapper won't split it.

Why flush plugs and not downward posts: any post that protrudes below the
ceiling drops the servo lower and makes the spline reach worse (that's the very
gap drive_rod_v1 is fixing).  Flush plugs keep the servo where it is.

PRINT: PETG, on end, with a brim (they're tiny).  No supports.
"""

from __future__ import annotations

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 48

HOLE_D = 4.2  # base insert holes
PLUG_D = 4.1  # glue slip-fit
PLUG_H = 6.0
PILOT_D = 2.6  # M3 self-tap
PILOT_DEPTH = 5.5
CHAMFER = 0.5
COUNT = 6
PITCH = 8.0  # spacing on the plate


def cyl(r, z0, z1, cx=0.0, cy=0.0):
    c = cylinder(radius=r, height=z1 - z0, sections=SEG)
    c.apply_translation([cx, cy, (z0 + z1) / 2])
    return c


def one(cx=0.0, cy=0.0):
    body = cyl(PLUG_D / 2, 0, PLUG_H, cx, cy)
    # ease both ends: insertion lead-in + screw start
    lead = trimesh.creation.cone(radius=PLUG_D / 2, height=CHAMFER, sections=SEG)
    lead.apply_translation([cx, cy, 0])  # tip down at z=0
    top = trimesh.creation.cone(radius=PLUG_D / 2, height=CHAMFER, sections=SEG)
    top.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    top.apply_translation([cx, cy, PLUG_H])
    body = trimesh.boolean.difference([body, lead, top], engine="manifold")
    pilot = cyl(PILOT_D / 2, PLUG_H - PILOT_DEPTH, PLUG_H + 0.1, cx, cy)
    return trimesh.boolean.difference([body, pilot], engine="manifold")


def main():
    plug = one()
    assert plug.is_watertight, "plug not watertight"
    plug.export("saddle_post_v1.stl")  # single plug

    n = int(np.ceil(np.sqrt(COUNT)))
    plate = []
    for k in range(COUNT):
        r, c = divmod(k, n)
        plate.append(one(c * PITCH, r * PITCH))
    grid = trimesh.util.concatenate(plate)
    grid.export("saddle_post_v1_x6.stl")

    print(f"saddle_post_v1  O{PLUG_D}x{PLUG_H}  pilot O{PILOT_D}  vol {plug.volume/1000:.2f} cm3 each")
    print(f"  [{'ok ' if PLUG_D < HOLE_D else 'FAIL'}] glue slip-fit O{PLUG_D} < hole O{HOLE_D}")
    print(f"  [{'ok ' if PILOT_D < PLUG_D - 1.0 else 'FAIL'}] pilot leaves wall {(PLUG_D-PILOT_D)/2:.2f} mm (glued, backed by the hole wall)")
    print("  ..  print 6: 2 for the saddle ceiling, 4 for the lid; see saddle_post_v1_x6.stl")


if __name__ == "__main__":
    main()
