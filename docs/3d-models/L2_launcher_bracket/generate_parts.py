"""L2_launcher_bracket — production two-wheel launcher (BOTH motor hole sets).

Geometry (X = fire direction, Y = motor axis/depth, Z = up; nip at origin):
- Two 60mm URIMPAVIDO rubber wheels (28mm wide), FRONT/BACK arrangement,
  wheel centers 97mm apart -> 37mm nip (3mm squeeze on the 40mm ball)
- Ball drops STRAIGHT DOWN the vertical chute (44mm inner) into the wheel V,
  fired forward (+X); vertical drop keeps feed decoupled from aim
- 2x A2212 1400KV, one per wheel (ch3 top / ch4 bottom per channel_map.py)

Motor mounts — BOTH A2212 hole sets, plain M3 holes (Ø3.4) at 45 deg positions:
- OUTER (primary): pitch radius 15mm  |  INNER: pitch radius 11mm
- Ø6.5 x 3mm counterbores on the FRONT (wheel) face for M3 cap heads
- Ø8 shaft clearance + Ø30 bell relief on the back (motor) face
Motors mount on the BACK (-Y) face; wheels ride the shafts in front.

Top flange (70x60x5) = interface the feed unit couples onto (coupler is a
separate frame-coupled part, not yet designed).

VERIFY with L1_motor_mount_coupon BEFORE printing.
Print: PETG, plate flat on bed, support under chute mouth + flange.
"""

import numpy as np
import trimesh

XSEP = 97.0
WMID = 20.0
PLATE_L, PLATE_T, PLATE_H = 150.0, 5.0, 96.0
CHUTE_IN, CHUTE_WALL, CHUTE_H = 44.0, 3.0, 62.0
PR_OUT, PR_IN = 15.0, 11.0
HOLE_D = 3.4
CBORE_D, CBORE_DEEP = 6.5, 3.0
SHAFT_D, BELL_D, BELL_RELIEF = 8.0, 30.0, 2.5


def box(l, w, h, x=0, y=0, z=0):
    b = trimesh.creation.box(extents=[l, w, h])
    b.apply_translation([x, y, z])
    return b


def ycyl(r, y0, y1, x=0, z=0, s=48):
    c = trimesh.creation.cylinder(radius=r, height=(y1 - y0), sections=s)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def motor_holes(part, cx, cz, y0, y1):
    for pr in (PR_OUT, PR_IN):
        for deg in (45, 135, 225, 315):
            a = np.radians(deg)
            hx, hz = cx + pr * np.cos(a), cz + pr * np.sin(a)
            part = part.difference(ycyl(HOLE_D / 2, y0 - 1, y1 + 1, x=hx, z=hz), engine="manifold")
            part = part.difference(
                ycyl(CBORE_D / 2, y1 - CBORE_DEEP, y1 + 1, x=hx, z=hz), engine="manifold"
            )
    part = part.difference(ycyl(SHAFT_D / 2, y0 - 1, y1 + 1, x=cx, z=cz), engine="manifold")
    part = part.difference(
        ycyl(BELL_D / 2, y0 - 1, y0 + BELL_RELIEF, x=cx, z=cz), engine="manifold"
    )
    return part


def build():
    plate = box(PLATE_L, PLATE_T, PLATE_H, y=-PLATE_T / 2)
    for cxm in (-XSEP / 2, XSEP / 2):
        plate = motor_holes(plate, cxm, 0, -PLATE_T, 0)
    co = CHUTE_IN + 2 * CHUTE_WALL
    chute = box(co, co, CHUTE_H, x=0, y=WMID, z=64).difference(
        box(CHUTE_IN, CHUTE_IN, CHUTE_H + 2, x=0, y=WMID, z=64), engine="manifold"
    )
    flange = box(70, 60, 5, x=0, y=WMID - 3, z=97)
    gus = box(6, CHUTE_IN, 44, x=0, y=WMID, z=40)
    return (
        plate.union(chute, engine="manifold")
        .union(flange, engine="manifold")
        .union(gus, engine="manifold")
    )


if __name__ == "__main__":
    m = build()
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    assert m.is_watertight
    m.export("L2_launcher_bracket.stl")
    print(
        "L2_launcher_bracket.stl", [round(x, 1) for x in m.extents], "watertight", m.is_watertight
    )
