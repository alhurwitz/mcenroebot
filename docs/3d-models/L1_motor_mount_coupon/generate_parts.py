"""L1_motor_mount_coupon — A2212 fit-check coupon with BOTH hole sets.

AJ's A2212 has two concentric hole sets. This coupon (and the launcher bracket)
carries BOTH as plain M3 clearance holes so either set can be used:
- OUTER set (primary): pitch radius 15mm (~30mm diagonal; test-card pad E,
  fit cleaner toward the outer end)
- INNER set: pitch radius 11mm (~22mm diagonal; test-card pad C)
All 8 holes at 45/135/225/315 deg, Ø3.4 through, with Ø6.5 x 3mm counterbores
on the FRONT face so M3 cap heads sit flush. Ø8 center shaft clearance.
Motor mounts against the BACK face; screws pass front->back into the motor.

Print: PLA, flat, ~5 min. Bolt the A2212 on via the OUTER holes: all four
screws catch, bell centered, heads flush -> clears L2_launcher_bracket.
If outer is off, report direction; inner is the fallback.
"""

import numpy as np
import trimesh

PLATE, T = 52.0, 5.0
PR_OUT, PR_IN = 15.0, 11.0
HOLE_D = 3.4
CBORE_D, CBORE_DEEP = 6.5, 3.0
SHAFT_D = 8.0


def box(l, w, h, x=0, y=0, z=0):
    b = trimesh.creation.box(extents=[l, w, h])
    b.apply_translation([x, y, z])
    return b


def ycyl(r, y0, y1, x=0, z=0, s=48):
    c = trimesh.creation.cylinder(radius=r, height=(y1 - y0), sections=s)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def build():
    p = box(PLATE, T, PLATE, y=T / 2)
    for pr in (PR_OUT, PR_IN):
        for deg in (45, 135, 225, 315):
            a = np.radians(deg)
            hx, hz = pr * np.cos(a), pr * np.sin(a)
            p = p.difference(ycyl(HOLE_D / 2, -1, T + 1, x=hx, z=hz), engine="manifold")
            p = p.difference(
                ycyl(CBORE_D / 2, T - CBORE_DEEP, T + 1, x=hx, z=hz), engine="manifold"
            )
    p = p.difference(ycyl(SHAFT_D / 2, -1, T + 1), engine="manifold")
    return p


if __name__ == "__main__":
    m = build()
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    assert m.is_watertight
    m.export("L1_motor_mount_coupon.stl")
    print(
        "L1_motor_mount_coupon.stl", [round(x, 1) for x in m.extents], "watertight", m.is_watertight
    )
