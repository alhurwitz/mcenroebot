"""L1_motor_mount_coupon — A2212 fit-check coupon (bare motor, single hole set).

Bare A2212 (silver X-mount NOT used) has ONE mounting hole set on its face:
4 tapped M3 holes on a square at pitch RADIUS 11mm (~22mm diagonal; confirmed
best fit = test-card pad C). Holes at 45/135/225/315 deg.

This coupon: 4x Ø3.4 M3 clearance holes at that pattern, Ø6.5 x 3mm
counterbores on the FRONT face (cap heads sit flush), Ø8 center shaft
clearance. Motor mounts against the BACK face; screws pass front->back into
the motor's tapped holes.

Print: PLA, flat, ~5 min. Bolt an A2212 on: all four screws catch, plate flat
(not rocking on the bell), heads flush -> clears L2_launcher_bracket.
"""
import numpy as np
import trimesh

PLATE, T = 48.0, 5.0
PITCH_R = 11.0          # confirmed: single hole set, pitch radius (mm)
HOLE_D = 3.4            # M3 clearance
CBORE_D, CBORE_DEEP = 6.5, 3.0
SHAFT_D = 8.0


def box(l, w, h, x=0, y=0, z=0):
    b = trimesh.creation.box(extents=[l, w, h]); b.apply_translation([x, y, z]); return b

def ycyl(r, y0, y1, x=0, z=0, s=48):
    c = trimesh.creation.cylinder(radius=r, height=(y1 - y0), sections=s)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z]); return c


def build():
    p = box(PLATE, T, PLATE, y=T / 2)
    for deg in (45, 135, 225, 315):
        a = np.radians(deg)
        hx, hz = PITCH_R * np.cos(a), PITCH_R * np.sin(a)
        p = p.difference(ycyl(HOLE_D / 2, -1, T + 1, x=hx, z=hz), engine="manifold")
        p = p.difference(ycyl(CBORE_D / 2, T - CBORE_DEEP, T + 1, x=hx, z=hz), engine="manifold")
    p = p.difference(ycyl(SHAFT_D / 2, -1, T + 1), engine="manifold")
    return p


if __name__ == "__main__":
    m = build()
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces())
    assert m.is_watertight
    m.export("L1_motor_mount_coupon.stl")
    print("L1_motor_mount_coupon.stl", [round(x, 1) for x in m.extents], "watertight", m.is_watertight)
