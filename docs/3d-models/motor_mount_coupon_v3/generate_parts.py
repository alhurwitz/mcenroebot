#!/usr/bin/env python3
"""motor_mount_coupon_v3 — A2212 bare-motor mount test coupon.

SINGLE hole set (silver X-mount not used):
  4x M3 plain clearance holes, pitch radius 11 mm (test-card pad C,
  4th-largest pad / largest on bottom row), at 45/135/225/315 deg.
  O6.5 x 3 mm cap-head counterbores on the screw side.
  O8 shaft clearance. O17 x 2 mm hub relief on the motor side.

Stack: screw -> coupon -> motor (counterbores face AWAY from the motor).
All mm. trimesh + manifold3d.
"""
import numpy as np
import trimesh

PLATE = 44.0        # square coupon side
T = 6.0             # plate thickness
PR = 11.0           # M3 pitch radius (pad C)
M3_R = 1.7          # M3 clearance radius
CB_R = 3.25         # counterbore radius (O6.5)
CB_D = 3.0          # counterbore depth
SHAFT_R = 4.0       # O8 shaft clearance
HUB_R = 8.5         # O17 hub relief
HUB_D = 2.0         # hub relief depth (motor side)
ANGLES = (45, 135, 225, 315)


def zcyl(r, z0, z1, x=0.0, y=0.0, s=64):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=s)
    c.apply_translation([x, y, (z0 + z1) / 2])
    return c


def build():
    # plate spans z 0..T; motor side = z=T (top), screw side = z=0 (bottom)
    plate = trimesh.creation.box(extents=[PLATE, PLATE, T])
    plate.apply_translation([0, 0, T / 2])

    cuts = [zcyl(SHAFT_R, -1, T + 1),            # shaft through
            zcyl(HUB_R, T - HUB_D, T + 1)]        # hub relief, motor side
    for a in ANGLES:
        x, y = PR * np.cos(np.radians(a)), PR * np.sin(np.radians(a))
        cuts.append(zcyl(M3_R, -1, T + 1, x, y))          # M3 through
        cuts.append(zcyl(CB_R, -1, CB_D, x, y))            # counterbore, screw side
    part = plate.difference(cuts, engine="manifold")
    part.merge_vertices()
    part.update_faces(part.nondegenerate_faces())
    return part


if __name__ == "__main__":
    p = build()
    p.export("motor_mount_coupon_v3.stl")
    print("extents", [round(v, 1) for v in p.extents], "watertight", p.is_watertight)
