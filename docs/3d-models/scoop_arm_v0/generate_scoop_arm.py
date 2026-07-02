"""generate_scoop_arm.py

The rocking "scoop / one-ball airlock" arm for the V4 discharge mechanism.
Mounts directly on a spare V2 MG996R (25T, Ø5.9 spline). One pocket cradles a single
40 mm ball at the chute exit, the body seals the chute, a ~70 deg rock delivers the ball
level to the launch nip. One rock = one ball, geometrically — cannot surge.

Reuses the disk's pocket numbers (Ø42 = ball+2, 1 mm lip). Pocket is an OPEN cradle here
(scoop), not a blind cup, so the ball rolls out at discharge.

Local frame: pivot at origin, arm points +X (distal), width along +Y (servo on the -Y
face), cradle opens toward +X. Mount: 25T round self-cut socket on the -Y face + an M3
retaining-screw bore from +Y; an 8 mm pivot stub on +Y rides a bushing in the chute's
far wall so the arm isn't cantilevered off the spline alone.

GEOMETRY LINK TO THE FRAME:  chute-exit -> nip distance = 2*cradle_radius*sin(rock/2),
where cradle_radius = arm_len + head_r + (pocket_r - cup_depth) ~ 68 mm here, giving
~78 mm of throw at rock=70 deg. Change arm_len to match your measured nip gap.

trimesh + manifold, same pattern as the disk/coupler. Units mm. PETG.
"""

import numpy as np
import trimesh

# ---- ball / cradle -------------------------------------------------------------------
BALL_D = 40.0
POCKET_D = BALL_D + 2.0  # 42, reused from the disk
POCKET_R = POCKET_D / 2.0
CUP_DEPTH = 22.0  # how far the ball nests (mouth stays >= ball dia)
LIP = 1.0

# ---- arm -----------------------------------------------------------------------------
ARM_LEN = 45.0  # pivot -> cradle; sets the nip throw (see header)
ROCK_DEG = 70.0  # informational; the frame uses this
WIDTH = 38.0  # fits inside a 43 mm single-file channel
HUB_R = 11.0
HEAD_R = 24.0
BRIDGE_HALF = 11.0

# ---- mount (MG996R 25T) --------------------------------------------------------------
SPLINE_BORE_D = 5.7  # round self-cut (5.5-5.8 to tune); spline is Ø5.9 25T
SOCKET_DEPTH = 5.0
SCREW_CLEAR_D = 3.4  # M3 retaining screw shank
SCREW_HEAD_D = 6.2  # M3 socket-head counterbore
PIVOT_STUB_D = 8.0  # +Y support stub
PIVOT_STUB_LEN = 6.0

SECTIONS = 160
EPS = 0.3


def ycyl(r, y0, y1, x=0.0, z=0.0, sec=SECTIONS):
    """Cylinder with its axis along +Y, spanning y0..y1, centred at (x,z)."""
    c = trimesh.creation.cylinder(radius=r, height=(y1 - y0), sections=sec)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2.0, z])
    return c


def _circle_pts_y(r, y, n=SECTIONS):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([r * np.cos(a), np.full(n, y), r * np.sin(a)])


def y_frustum(r0, y0, r1, y1):
    pts = np.vstack([_circle_pts_y(r0, y0), _circle_pts_y(r1, y1)])
    return trimesh.Trimesh(vertices=pts).convex_hull


def build():
    W = WIDTH
    # ---- body: hub + head + bridge, all Y-axis solids ----
    hub = ycyl(HUB_R, 0, W)
    head = ycyl(HEAD_R, 0, W, x=ARM_LEN)
    bridge = trimesh.creation.box(extents=[ARM_LEN, W, 2 * BRIDGE_HALF])
    bridge.apply_translation([ARM_LEN / 2.0, W / 2.0, 0])
    body = hub.union(head, engine="manifold").union(bridge, engine="manifold")

    # ---- cradle: cylindrical valley carved into the +X face, opens +X ----
    head_face = ARM_LEN + HEAD_R
    xc = head_face + POCKET_R - CUP_DEPTH  # cylinder centre for the wanted depth
    cradle = ycyl(POCKET_R, -EPS, W + EPS, x=xc)
    body = body.difference(cradle, engine="manifold")

    # ---- mount on -Y face ----
    socket = ycyl(SPLINE_BORE_D / 2.0, -EPS, SOCKET_DEPTH)  # spline socket from y=0
    screw = ycyl(SCREW_CLEAR_D / 2.0, SOCKET_DEPTH - EPS, W + EPS)  # clearance to +Y
    head_cb = ycyl(SCREW_HEAD_D / 2.0, W - 4.0, W + EPS)  # counterbore on +Y face
    body = body.difference(socket, engine="manifold")
    body = body.difference(screw, engine="manifold")
    body = body.difference(head_cb, engine="manifold")

    # ---- +Y pivot stub ----
    stub = ycyl(PIVOT_STUB_D / 2.0, W, W + PIVOT_STUB_LEN)
    body = body.union(stub, engine="manifold")
    # re-open the screw counterbore through the stub centre so the screw still seats
    body = body.difference(
        ycyl(SCREW_CLEAR_D / 2.0, W - 4.0, W + PIVOT_STUB_LEN + EPS), engine="manifold"
    )
    body = body.difference(
        ycyl(SCREW_HEAD_D / 2.0, W + PIVOT_STUB_LEN - 4.0, W + PIVOT_STUB_LEN + EPS),
        engine="manifold",
    )
    return body


def main():
    part = build()
    part.merge_vertices()
    part.update_faces(part.nondegenerate_faces())
    out = "scoop_arm_v0.stl"
    part.export(out)
    ext = part.extents
    cradle_radius = ARM_LEN + HEAD_R + (POCKET_R - CUP_DEPTH)
    throw = 2 * cradle_radius * np.sin(np.radians(ROCK_DEG) / 2)
    print("scoop arm v0")
    print(
        f"  arm_len / rock      : {ARM_LEN:.0f} mm / {ROCK_DEG:.0f} deg  ->  nip throw ~{throw:.0f} mm"
    )
    print(f"  cradle              : Ø{POCKET_D:.0f} valley, {CUP_DEPTH:.0f} deep, opens distally")
    print(f"  width               : {WIDTH:.0f} mm  (for a {WIDTH + 5:.0f} mm channel)")
    print(
        f"  mount               : Ø{SPLINE_BORE_D} self-cut 25T socket + M3 retainer + Ø{PIVOT_STUB_D} stub"
    )
    print(f"  bbox                : {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm")
    print(f"  watertight          : {part.is_watertight} | {part.volume / 1000:.1f} cm^3")
    print(f"  -> {out}")
    return part


if __name__ == "__main__":
    main()
