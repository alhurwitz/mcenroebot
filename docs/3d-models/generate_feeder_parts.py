"""
McEnroe V4 (feeder) — parametric STL generator.

Run: python3 generate_feeder_parts.py
Outputs (in this folder):
    F1_escapement_disk.stl
    F2_hopper_cone.stl
    F3_auger_screw.stl
    F4_auger_tube.stl
    F5_launch_wheel.stl

All units in millimeters. Edit the constants block to tune the design.
Mirrors the idiom of generate_parts.py: trimesh primitives + boolean CSG.
"""

from __future__ import annotations

import os

import numpy as np
import trimesh
from trimesh.creation import cylinder

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Constants — edit these to tune the design
# ---------------------------------------------------------------------------

# Ball
BALL_D = 40.0
BALL_R = BALL_D / 2.0

# Hardware
M3_CLEAR = 3.4
M3_TAP = 2.8
WALL = 3.0

# 608 skate bearing (disk + auger shaft support)
BEARING_OD = 22.0
BEARING_ID = 8.0
BEARING_THICK = 7.0
ROD_D = 8.0  # 8 mm steel rod (auger core + disk pivot)

# --- F1 escapement disk -----------------------------------------------------
DISK_OD = 90.0
DISK_T = 26.0  # >= pocket depth + floor
POCKET_D = 42.0  # ball + 2 mm
POCKET_DEPTH = 22.0
POCKET_CENTER_R = 22.0  # pocket center from disk axis (fits within 45 mm OD)
HORN_BC = 16.0  # servo-horn screw bolt circle (4x M3) on the underside

# --- F2 hopper cone ---------------------------------------------------------
HOP_TOP_ID = 200.0
HOP_OUTLET_ID = 50.0
HOP_WALL_ANGLE_DEG = 62.0  # from horizontal; > 60 so 40 mm balls don't bridge
HOP_COLLAR_H = 12.0  # straight collar at outlet, sits over the disk

# --- F3 auger screw ---------------------------------------------------------
SCREW_CORE_OD = 14.0
SCREW_FLIGHT_OD = 44.0
SCREW_PITCH = 55.0
SCREW_TURNS = 2  # integer turns => flights align when segments stack
SCREW_FLIGHT_THK = 2.6  # axial thickness of the flight
SCREW_THETA_STEPS = 48  # per turn

# --- F4 auger tube ----------------------------------------------------------
TUBE_ID = 46.0
TUBE_WALL = 3.0
TUBE_LEN = 112.0  # ~ matches the screw segment
TUBE_SOCKET_H = 15.0  # female socket depth (next section's OD nests in)
TUBE_SOCKET_CLEAR = 0.4

# --- F5 launch wheel --------------------------------------------------------
WHEEL_OD = 55.0
WHEEL_W = 18.0
WHEEL_BORE = 5.0  # MATCH to your collet/shaft adapter — see README
WHEEL_GROOVE_D = 3.0  # depth of the central tread groove (for an O-ring/band)
WHEEL_GROOVE_W = 4.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def T(mesh, dx=0.0, dy=0.0, dz=0.0):
    mesh.apply_translation([dx, dy, dz])
    return mesh


def RX(mesh, deg):
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0]))
    return mesh


def RY(mesh, deg):
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0]))
    return mesh


def cyl(d, h, sections=64):
    """Solid cylinder, axis = Z, centered at origin."""
    return cylinder(radius=d / 2.0, height=h, sections=sections)


def frustum(r_bottom, r_top, h, sections=96):
    """Watertight solid frustum (truncated cone), base at z=0, axis +Z."""
    ang = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    bot = np.column_stack([r_bottom * np.cos(ang), r_bottom * np.sin(ang), np.zeros(sections)])
    top = np.column_stack([r_top * np.cos(ang), r_top * np.sin(ang), np.full(sections, h)])
    cb = np.array([[0, 0, 0.0]])
    ct = np.array([[0, 0, h]])
    verts = np.vstack([bot, top, cb, ct])
    ib0, it0 = 0, sections
    icb, ict = 2 * sections, 2 * sections + 1
    faces = []
    for i in range(sections):
        j = (i + 1) % sections
        # side
        faces.append([ib0 + i, ib0 + j, it0 + j])
        faces.append([ib0 + i, it0 + j, it0 + i])
        # bottom cap (normal -Z)
        faces.append([icb, ib0 + j, ib0 + i])
        # top cap (normal +Z)
        faces.append([ict, it0 + i, it0 + j])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=True)
    m.fix_normals()
    return m


def helical_screw(core_od, flight_od, pitch, turns, flight_thk, theta_steps):
    """Watertight single-start screw: core cylinder + a helical flight slab.

    The flight is a thin helicoid of axial thickness `flight_thk`, swept from
    z=0 up to z=pitch*turns. Integer `turns` => the flight start and end share
    the same angular position, so stacked segments form a continuous screw.
    """
    r_core = core_od / 2.0
    r_out = flight_od / 2.0
    r_in = r_core - 0.5  # overlap into the core so the union is clean
    n = int(theta_steps * turns) + 1
    theta = np.linspace(0.0, 2 * np.pi * turns, n)
    z = pitch * theta / (2 * np.pi)

    verts = []
    for i in range(n):
        c, s = np.cos(theta[i]), np.sin(theta[i])
        zb = z[i]
        verts.append([r_in * c, r_in * s, zb])  # 0 inner-bottom
        verts.append([r_out * c, r_out * s, zb])  # 1 outer-bottom
        verts.append([r_in * c, r_in * s, zb + flight_thk])  # 2 inner-top
        verts.append([r_out * c, r_out * s, zb + flight_thk])  # 3 outer-top
    verts = np.array(verts)

    def vid(i, k):
        return 4 * i + k

    faces = []
    for i in range(n - 1):
        ib0, ob0, it0, ot0 = vid(i, 0), vid(i, 1), vid(i, 2), vid(i, 3)
        ib1, ob1, it1, ot1 = vid(i + 1, 0), vid(i + 1, 1), vid(i + 1, 2), vid(i + 1, 3)
        # bottom helicoid surface
        faces += [[ib0, ob0, ob1], [ib0, ob1, ib1]]
        # top helicoid surface
        faces += [[it0, it1, ot1], [it0, ot1, ot0]]
        # outer edge wall
        faces += [[ob0, ot0, ot1], [ob0, ot1, ob1]]
        # inner edge wall
        faces += [[ib0, ib1, it1], [ib0, it1, it0]]
    # end caps (start i=0, end i=n-1)
    s0 = [vid(0, 0), vid(0, 1), vid(0, 3), vid(0, 2)]
    faces += [[s0[0], s0[1], s0[2]], [s0[0], s0[2], s0[3]]]
    e = n - 1
    se = [vid(e, 0), vid(e, 1), vid(e, 3), vid(e, 2)]
    faces += [[se[0], se[2], se[1]], [se[0], se[3], se[2]]]

    flight = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=True)
    flight.fix_normals()

    total_h = pitch * turns + flight_thk
    core = cyl(core_od, total_h, sections=96)
    T(core, 0, 0, total_h / 2.0)  # base at z=0

    screw = trimesh.boolean.union([core, flight])

    # bore the rod hole + a radial grub-screw tap
    bore = cyl(ROD_D + 0.4, total_h * 3, sections=48)
    screw = screw.difference(bore)
    grub = cyl(M3_TAP, core_od * 3, sections=24)
    RY(grub, 90)
    T(grub, 0, 0, total_h / 2.0)
    screw = screw.difference(grub)
    return screw


# ---------------------------------------------------------------------------
# F1: escapement disk
# ---------------------------------------------------------------------------


def make_escapement_disk():
    """Single-pocket indexing disk. One pocket scoops a ball at the load
    station and drops it at discharge; the solid face blocks the hopper outlet
    everywhere else, so metering is geometric. Bearing seat (608) + 8 mm pivot
    bore; four M3 holes on the underside couple to a continuous-rotation servo
    horn."""
    disk = cyl(DISK_OD, DISK_T, sections=96)
    T(disk, 0, 0, DISK_T / 2.0)

    # the ball pocket (open top), with a 1 mm chamfer at the lip
    pocket = cyl(POCKET_D, POCKET_DEPTH * 2, sections=64)
    T(pocket, POCKET_CENTER_R, 0, DISK_T - POCKET_DEPTH + POCKET_DEPTH)  # top open
    disk = disk.difference(pocket)
    cham = trimesh.creation.cone(radius=POCKET_D / 2 + 1.0, height=2.0, sections=64)
    # invert cone to form a lip chamfer ring at the pocket mouth
    cham.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    T(cham, POCKET_CENTER_R, 0, DISK_T + 1.0)
    disk = disk.difference(cham)

    # central 8 mm pivot bore (thru) + 608 counterbore from the bottom
    bore = cyl(ROD_D + 0.2, DISK_T * 3, sections=48)
    disk = disk.difference(bore)
    cbore = cyl(BEARING_OD + 0.2, BEARING_THICK + 0.4, sections=64)
    T(cbore, 0, 0, (BEARING_THICK + 0.4) / 2.0)  # from bottom face up
    disk = disk.difference(cbore)

    # 4x M3 servo-horn holes on the underside (do not go all the way through)
    for ang in (0, 90, 180, 270):
        x = HORN_BC / 2 * np.cos(np.radians(ang))
        y = HORN_BC / 2 * np.sin(np.radians(ang))
        h = cyl(M3_CLEAR, 10.0, sections=24)
        T(h, x, y, 4.0)  # 8 mm deep from bottom
        disk = disk.difference(h)
    return disk


# ---------------------------------------------------------------------------
# F2: hopper cone
# ---------------------------------------------------------------------------


def make_hopper_cone():
    r_top_in = HOP_TOP_ID / 2.0
    r_out_in = HOP_OUTLET_ID / 2.0
    h = (r_top_in - r_out_in) * np.tan(np.radians(HOP_WALL_ANGLE_DEG))
    inner = frustum(r_out_in, r_top_in, h + 1.0, sections=120)  # taller for clean cut
    T(inner, 0, 0, -0.5)
    outer = frustum(r_out_in + WALL, r_top_in + WALL, h, sections=120)
    shell = outer.difference(inner)

    # straight collar at the outlet (sits over the disk)
    collar_out = cyl(HOP_OUTLET_ID + 2 * WALL, HOP_COLLAR_H, sections=96)
    T(collar_out, 0, 0, -HOP_COLLAR_H / 2.0)
    collar_in = cyl(HOP_OUTLET_ID, HOP_COLLAR_H * 2, sections=96)
    T(collar_in, 0, 0, -HOP_COLLAR_H / 2.0)
    collar = collar_out.difference(collar_in)
    return trimesh.boolean.union([shell, collar])


# ---------------------------------------------------------------------------
# F3 / F4 / F5
# ---------------------------------------------------------------------------


def make_auger_screw():
    return helical_screw(
        SCREW_CORE_OD,
        SCREW_FLIGHT_OD,
        SCREW_PITCH,
        SCREW_TURNS,
        SCREW_FLIGHT_THK,
        SCREW_THETA_STEPS,
    )


def make_auger_tube():
    """Hollow tube section with a female socket at the top end; the plain OD of
    the next section nests into it. The bottom (inlet) section needs a side
    window cut for ball entry — see README."""
    od = TUBE_ID + 2 * TUBE_WALL
    body_h = TUBE_LEN - TUBE_SOCKET_H
    # plain lower body: OD/ID over the lower (body_h) length
    lower = cyl(od, body_h, sections=96)
    T(lower, 0, 0, body_h / 2.0)
    # belled socket: enlarged OD + enlarged ID over the top TUBE_SOCKET_H, so the
    # plain OD of the next section slips into ID = od + clearance
    socket_id = od + 2 * TUBE_SOCKET_CLEAR
    socket_od = socket_id + 2 * TUBE_WALL
    bell = cyl(socket_od, TUBE_SOCKET_H, sections=96)
    T(bell, 0, 0, body_h + TUBE_SOCKET_H / 2.0)
    tube = trimesh.boolean.union([lower, bell])
    # bore: ID through the body, widening to socket_id through the bell
    bore_body = cyl(TUBE_ID, body_h * 2 + 1, sections=96)
    T(bore_body, 0, 0, body_h)  # spans below->into body
    tube = tube.difference(bore_body)
    bore_bell = cyl(socket_id, TUBE_SOCKET_H * 2, sections=96)
    T(bore_bell, 0, 0, TUBE_LEN)  # opens at the top face, down into the bell
    tube = tube.difference(bore_bell)
    return tube


def make_launch_wheel():
    """Drive wheel for a launch motor. Plain bore + grub screw; central tread
    groove seats a rubber O-ring/band for grip. MATCH WHEEL_BORE to your collet
    adapter."""
    wheel = cyl(WHEEL_OD, WHEEL_W, sections=96)
    T(wheel, 0, 0, WHEEL_W / 2.0)
    # central tread groove
    groove_out = cyl(WHEEL_OD + 1.0, WHEEL_GROOVE_W, sections=96)
    groove_in = cyl(WHEEL_OD - 2 * WHEEL_GROOVE_D, WHEEL_GROOVE_W, sections=96)
    groove = groove_out.difference(groove_in)
    T(groove, 0, 0, WHEEL_W / 2.0)
    wheel = wheel.difference(groove)
    # bore + grub
    bore = cyl(WHEEL_BORE, WHEEL_W * 3, sections=48)
    wheel = wheel.difference(bore)
    grub = cyl(M3_TAP, WHEEL_OD * 3, sections=24)
    RY(grub, 90)
    T(grub, 0, 0, WHEEL_W / 2.0)
    wheel = wheel.difference(grub)
    return wheel


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

PARTS = [
    ("F1_escapement_disk.stl", make_escapement_disk),
    ("F2_hopper_cone.stl", make_hopper_cone),
    ("F3_auger_screw.stl", make_auger_screw),
    ("F4_auger_tube.stl", make_auger_tube),
    ("F5_launch_wheel.stl", make_launch_wheel),
]


def main():
    for fname, fn in PARTS:
        print(f"Building {fname} ...")
        m = fn()
        bb = m.bounding_box.extents
        print(
            f"  watertight={m.is_watertight}  volume_ok={m.is_volume}  "
            f"verts={len(m.vertices)}  faces={len(m.faces)}  "
            f"bbox={bb[0]:.1f}x{bb[1]:.1f}x{bb[2]:.1f}mm"
        )
        out = os.path.join(HERE, fname)
        m.export(out)
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
