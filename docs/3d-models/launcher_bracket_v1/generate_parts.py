"""Regenerate launcher_bracket_v1: add the proven coupon motor mounts.

Inherited geometry (funnel chute, mounting plate, top flange) is carried in as
launcher_bracket_v1_base.stl -- the full parametric source for that body was not
retained; only the A2212 mount pattern is "solved" and is defined parametrically
here. This script cuts the solved mount (Ø18 bore + 4 radial M3 slots) into each
of the two motor stations, matching motor_mount_coupon exactly, and leaves the
funnel/chute/flange untouched.

A2212 pattern is UNMEASURED by design: keep nominal 16x19, absorb clone variance
with radial slots (M3 clearance, +/-2mm radial travel). A torqued screw clamps
anywhere in the slot. Slots are permanent -- they carry through to this part.

Regenerate:  python generate_parts.py   (needs trimesh + manifold3d)
"""

import numpy as np
import trimesh
from trimesh.creation import box, cylinder

MF = dict(engine="manifold")

# ---- solved mount parameters (identical to motor_mount_coupon) ----
BORE_D = 18.0  # boss/bell clearance
PATT_X = 16.0  # nominal A2212 bolt pattern, short axis -> plate X
PATT_Z = 19.0  # nominal A2212 bolt pattern, long axis  -> plate Z
M3_CLEAR = 3.6  # M3 clearance slot width
RADIAL_ELON = 2.0  # +/-2 mm radial travel to absorb clone variance
MOTOR_X = [-48.5, 48.5]  # two wheel/motor stations (97 mm centers, 60 mm wheels -> 37 mm nip)
MOTOR_Z = 0.0
PLATE_Y = (-8.0, 4.0)  # cut spans full plate depth (front skin + rear recess)


def y_cyl(dia, x, z, y0, y1):
    """Cylinder with its axis along +Y, centered at (x, *, z)."""
    c = cylinder(radius=dia / 2.0, height=(y1 - y0), sections=64)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2.0, z])
    return c


def radial_slot(cx, cz, hx, hz, y0, y1, width, elong):
    """Capsule slot on nominal hole (cx+hx, cz+hz); long axis = radial from the
    station center (cx,cz); swept through Y. Two Y-cylinder end caps + a box."""
    px, pz = cx + hx, cz + hz
    r = np.hypot(hx, hz)
    ux, uz = hx / r, hz / r  # radial unit vector
    inner = (px - ux * elong, pz - uz * elong)
    outer = (px + ux * elong, pz + uz * elong)
    caps = [y_cyl(width, inner[0], inner[1], y0, y1), y_cyl(width, outer[0], outer[1], y0, y1)]
    bx = box(extents=[2 * elong, (y1 - y0), width])  # X-long, Y-thru, Z-wide
    bx.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(uz, ux), [0, 1, 0]))
    bx.apply_translation([px, (y0 + y1) / 2.0, pz])
    return trimesh.boolean.union([*caps, bx], **MF)


def mount_cutter(cx, cz):
    parts = [y_cyl(BORE_D, cx, cz, *PLATE_Y)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts.append(
                radial_slot(
                    cx,
                    cz,
                    sx * PATT_X / 2.0,
                    sz * PATT_Z / 2.0,
                    PLATE_Y[0],
                    PLATE_Y[1],
                    M3_CLEAR,
                    RADIAL_ELON,
                )
            )
    return trimesh.boolean.union(parts, **MF)


def main():
    base = trimesh.load("launcher_bracket_v1_base.stl")
    cutters = [mount_cutter(x, MOTOR_Z) for x in MOTOR_X]
    result = trimesh.boolean.difference([base, *cutters], **MF)
    result.merge_vertices()
    result.update_faces(result.nondegenerate_faces())
    assert result.is_watertight, "result not watertight"
    result.export("launcher_bracket_v1.stl")
    print(
        "watertight:",
        result.is_watertight,
        "vol_cm3:",
        round(result.volume / 1000, 1),
        "bounds:",
        np.round(result.bounds, 1).tolist(),
    )


if __name__ == "__main__":
    main()
