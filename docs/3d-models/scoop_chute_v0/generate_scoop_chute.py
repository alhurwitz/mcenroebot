"""generate_scoop_chute.py  (+ assembly check)

A minimal single-file BENCH chute matched to scoop_arm_v0: inclined trough (single-file,
roof over the gate, no climb-over), a servo cradle that puts the MG996R spline on the arm
pivot, open nip end. Lets you bench-test metering today; the production chute (hopper
neck-down + exact nip alignment) follows the frame.

The chute is coordinated to the arm via the SAME pivot + arm_len + rock, so the cradle
reaches the chute exit at LOAD and clears the trough through the rock.
"""

import numpy as np
import trimesh

# ---- shared with the arm -------------------------------------------------------------
BALL_D = 40.0
BALL_R = 20.0
ARM_LEN = 45.0
ROCK_DEG = 70.0
THETA_LOAD = 118.0  # arm distal direction at LOAD (deg, machine X-Z)
THETA_DISCH = THETA_LOAD - ROCK_DEG
CRADLE_R = ARM_LEN + 24.0 + (21.0 - 22.0)  # cradle-centre radius from pivot (~68)

# ---- chute ---------------------------------------------------------------------------
CH_W = 43.0  # single-file inner width (ball + 3)
WALL = 3.0
FLOOR_T = 3.0
WALL_H = 46.0  # above the roof
ROOF_UNDER = BALL_D + 2.0  # 42, roof underside clearance
ROOF_T = 3.0
ROOF_LEN = 64.0  # roof covers the gate region
CH_LEN = 150.0  # ~3-4 balls of queue
INCLINE = 25.0

# ---- servo cradle (MG996R standard) --------------------------------------------------
SV_L = 40.8
SV_W = 20.4
SV_H = 40.0
EAR_PITCH = 49.5
EAR_HOLE = 3.2
SECTIONS = 96
EPS = 0.3


def place_arm(mesh, theta_deg):
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-theta_deg), [0, 1, 0]))
    return m


def cradle_center(theta_deg):
    t = np.radians(theta_deg)
    return np.array([CRADLE_R * np.cos(t), 0.0, CRADLE_R * np.sin(t)])


def build_chute():
    # local trough frame: +X' up-chute, Z'=0 floor top, walls/roof in Z'
    L = CH_LEN
    outer = trimesh.creation.box(extents=[L, CH_W + 2 * WALL, FLOOR_T + WALL_H])
    outer.apply_translation([L / 2.0, 0, (-FLOOR_T + WALL_H) / 2.0])
    cavity = trimesh.creation.box(extents=[L + 2 * EPS, CH_W, WALL_H + EPS])
    cavity.apply_translation([L / 2.0, 0, WALL_H / 2.0])
    trough = outer.difference(cavity, engine="manifold")
    # roof over the gate (near the exit X'=0)
    roof = trimesh.creation.box(extents=[ROOF_LEN, CH_W + 2 * WALL, ROOF_T])
    roof.apply_translation([ROOF_LEN / 2.0, 0, ROOF_UNDER + ROOF_T / 2.0])
    trough = trough.union(roof, engine="manifold")

    # orient: rotate so the trough rises up-chute (toward THETA_LOAD side) and the floor
    # sits under the lead ball; place the exit floor under the LOAD cradle.
    phi = 180.0 + INCLINE  # Y-rotation to point +X' up-and-left
    R = trimesh.transformations.rotation_matrix(np.radians(phi), [0, 1, 0])
    trough.apply_transform(R)

    C_L = cradle_center(THETA_LOAD)  # lead ball centre at exit
    n = np.array([np.sin(np.radians(INCLINE)), 0, np.cos(np.radians(INCLINE))])
    F0 = C_L - BALL_R * n  # floor point under the lead ball
    local_exit = R[:3, :3] @ np.array([6.0, 0, 0])  # a touch in from the exit, on the floor
    trough.apply_translation(F0 - local_exit)
    return trough


def build_servo_cradle():
    # simple open cradle holding the MG996R with the spline at the pivot (origin)
    # servo body hangs below the pivot along -Z; spline at top of body.
    body_top_to_spline = 8.0  # MG996R: case top to output ~ this
    cz = -(SV_H / 2.0 + body_top_to_spline)  # body centre below pivot
    shell = trimesh.creation.box(extents=[SV_L + 2 * WALL, SV_W + 2 * WALL, SV_H])
    shell.apply_translation([0, 0, cz])
    pocket = trimesh.creation.box(extents=[SV_L, SV_W, SV_H + EPS])
    pocket.apply_translation([0, 0, cz])
    cradle = shell.difference(pocket, engine="manifold")
    # ear shelf with two screw holes at the spline plane
    shelf = trimesh.creation.box(extents=[EAR_PITCH + 16, SV_W + 2 * WALL, WALL])
    shelf.apply_translation([0, 0, -body_top_to_spline - WALL / 2.0])
    cradle = cradle.union(shelf, engine="manifold")
    for sx in (-EAR_PITCH / 2.0, EAR_PITCH / 2.0):
        h = trimesh.creation.cylinder(radius=EAR_HOLE / 2.0, height=WALL + 2 * EPS, sections=48)
        h.apply_translation([sx, 0, -body_top_to_spline - WALL / 2.0])
        cradle = cradle.difference(h, engine="manifold")
    return cradle


def main():
    chute = build_chute()
    chute.merge_vertices()
    chute.update_faces(chute.nondegenerate_faces())
    chute.export("scoop_chute_v0.stl")
    cradle = build_servo_cradle()
    cradle.merge_vertices()
    cradle.update_faces(cradle.nondegenerate_faces())
    cradle.export("scoop_servo_cradle_v0.stl")
    print("chute   bbox", np.round(chute.extents, 1), "watertight", chute.is_watertight)
    print("cradle  bbox", np.round(cradle.extents, 1), "watertight", cradle.is_watertight)
    return chute, cradle


if __name__ == "__main__":
    main()
