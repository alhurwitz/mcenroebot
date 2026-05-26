"""
McEnroe V2 arm — parametric STL generator.

Run: python3 generate_parts.py
Outputs: 01_base_plate.stl ... 05_paddle_clamp.stl  in this folder.

All units in millimeters. Edit the constants block to tweak dimensions.
"""

from __future__ import annotations

import os

import numpy as np
import trimesh
from trimesh.creation import box, cylinder

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Constants — edit these to tune the design
# ---------------------------------------------------------------------------

# MG996R servo body (the aiming servos for yaw + pitch)
SERVO_W = 40.7  # length of body
SERVO_D = 19.7  # depth of body
SERVO_H = 42.9  # height of body (without ear tabs)
SERVO_EAR_THICK = 2.5
SERVO_EAR_EXTENT = 7.5  # how far ears stick out past the body on each side
SERVO_EAR_SCREW_D = 4.2  # M4 clearance for servo ear mounting screws
SERVO_EAR_SCREW_SPACING_X = 49.5  # center-to-center across the long axis
SERVO_EAR_SCREW_SPACING_Y = 10.0  # center-to-center across the short axis
SERVO_SHAFT_OFFSET_X = 9.8  # output shaft is offset from body center along X
SERVO_HORN_CLEAR_R = 12.0  # clearance hole radius for the round servo horn

# A2212 brushless motor (the swing motor)
BLDC_OD = 28.0  # body outer diameter
BLDC_BODY_LEN = 30.0  # length of motor body
BLDC_SHAFT_D = 3.17  # 1/8" shaft (3.17mm)
BLDC_MOUNT_BOLT_CIRCLE = 19.0  # bolt circle diameter for the X-pattern mount
BLDC_MOUNT_SCREW_D = 3.4  # M3 clearance

# 608 skate bearings (yaw axis + swing axis side support)
BEARING_OD = 22.0
BEARING_ID = 8.0
BEARING_THICK = 7.0

# Hardware
M3_CLEAR = 3.4  # M3 clearance hole
M3_TAP = 2.8  # tapping into plastic (heat-set insert if you have them)
M4_CLEAR = 4.4
WALL = 3.0  # default wall thickness — generous because PETG and load
PLATE_T = 5.0  # default plate thickness

# Arm geometry
SWING_ARM_LEN = 250.0  # distance from BLDC shaft to paddle center
SWING_ARM_W = 22.0  # arm width
SWING_ARM_T = 6.0  # arm thickness
PADDLE_BLADE_W = 158.0  # standard paddle blade width
PADDLE_BLADE_T = 7.0  # blade thickness (with rubber)
PADDLE_CLAMP_DEPTH = 35.0  # how deep the clamp grips the blade

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def Z(mesh, dz):
    """Translate mesh along +Z by dz (mutates and returns)."""
    mesh.apply_translation([0, 0, dz])
    return mesh


def T(mesh, dx=0, dy=0, dz=0):
    mesh.apply_translation([dx, dy, dz])
    return mesh


def RX(mesh, deg):
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0]))
    return mesh


def RY(mesh, deg):
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0]))
    return mesh


def RZ(mesh, deg):
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1]))
    return mesh


def hole(d, h, sections=48):
    """A cylinder for boolean subtraction, centered on origin, axis = Z."""
    c = cylinder(radius=d / 2, height=h, sections=sections)
    return c


def servo_pocket():
    """A negative volume for an MG996R-style servo, centered on its body.
    Includes the body cavity, ear cutouts, and ear screw holes (clearance)."""
    body = box((SERVO_W, SERVO_D, SERVO_H + 20))  # extra height so it punches all the way through
    body.apply_translation([0, 0, 10])  # shift so bottom is at z=-SERVO_H/2 - 10
    ears = box((SERVO_W + 2 * SERVO_EAR_EXTENT, SERVO_D, SERVO_EAR_THICK + 1))
    ears.apply_translation([0, 0, SERVO_H / 2 - 13])  # roughly where the ears sit on the body
    parts = [body, ears]
    # Ear screw clearance holes (4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = hole(SERVO_EAR_SCREW_D, 30)
            h.apply_translation(
                [
                    sx * SERVO_EAR_SCREW_SPACING_X / 2,
                    sy * SERVO_EAR_SCREW_SPACING_Y / 2,
                    SERVO_H / 2 - 13,
                ]
            )
            parts.append(h)
    return trimesh.util.concatenate(parts)


def bldc_mount_negatives():
    """Holes for an A2212-class motor: central shaft pass-through and a 4-screw X pattern.
    Returns a list of cylinder meshes oriented along Z, centered at origin."""
    cyls = []
    # Central shaft pass-through (slightly larger than shaft)
    cyls.append(hole(BLDC_SHAFT_D + 1.0, 40))
    # 4 mount screws on a bolt circle, X pattern (45° offsets)
    r = BLDC_MOUNT_BOLT_CIRCLE / 2.0
    for ang in (45, 135, 225, 315):
        c = hole(BLDC_MOUNT_SCREW_D, 40)
        c.apply_translation([r * np.cos(np.radians(ang)), r * np.sin(np.radians(ang)), 0])
        cyls.append(c)
    return cyls


# ---------------------------------------------------------------------------
# Part 1: Base plate
# ---------------------------------------------------------------------------


def make_base_plate():
    """Footprint that bolts to a heavy base. Holds J1 (yaw) servo pointing up.
    Also has a 608 bearing pocket on top center to take the radial load off
    the servo output shaft (the yaw bracket has a stub that rides in the
    bearing)."""
    plate_w = 110.0
    plate_d = 90.0
    plate_t = PLATE_T

    base = box((plate_w, plate_d, plate_t))
    base.apply_translation([0, 0, plate_t / 2])

    # Servo mount tower — a raised block in the middle that the servo drops into
    tower_w = SERVO_W + 2 * WALL + 2 * SERVO_EAR_EXTENT
    tower_d = SERVO_D + 2 * WALL
    tower_h = SERVO_H + 4  # a touch deeper so ears sit below the top surface
    tower = box((tower_w, tower_d, tower_h))
    tower.apply_translation([0, 0, plate_t + tower_h / 2])

    body = base.union(tower)

    # Carve out the servo pocket (centered, shaft poking up through the top)
    pocket = servo_pocket()
    pocket.apply_translation([0, 0, plate_t + tower_h / 2])
    body = body.difference(pocket)

    # 4 corner bolt-down slots (M4 clearance) for fastening to a heavy base
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = hole(M4_CLEAR, plate_t * 3)
            h.apply_translation([sx * (plate_w / 2 - 8), sy * (plate_d / 2 - 8), plate_t / 2])
            body = body.difference(h)

    return body


# ---------------------------------------------------------------------------
# Part 2: Yaw bracket  (rides on J1 horn, holds J2)
# ---------------------------------------------------------------------------


def make_yaw_bracket():
    """U-shaped bracket: bottom face bolts to J1 servo horn. Vertical wall
    holds J2 (pitch servo) on its side, so J2's output shaft points horizontally."""
    bot_w = 60.0
    bot_d = 60.0
    bot_t = 6.0

    bottom = box((bot_w, bot_d, bot_t))
    bottom.apply_translation([0, 0, bot_t / 2])

    # Vertical wall — tall enough to hold the pitch servo on its long axis
    wall_w = bot_w
    wall_t = WALL + SERVO_D  # wall must be thick enough to contain the servo body
    wall_h = SERVO_W + 2 * WALL + 2 * SERVO_EAR_EXTENT
    wall = box((wall_w, wall_t, wall_h))
    wall.apply_translation([0, bot_d / 2 - wall_t / 2, bot_t + wall_h / 2])

    body = bottom.union(wall)

    # Servo-horn screw circle (4-screw pattern at small radius) — bolt onto J1 horn
    for ang in (0, 90, 180, 270):
        r = 7.0
        h = hole(M3_CLEAR, bot_t * 3)
        h.apply_translation([r * np.cos(np.radians(ang)), r * np.sin(np.radians(ang)), bot_t / 2])
        body = body.difference(h)
    # Center hole for servo shaft clearance
    body = body.difference(
        hole(6.0, bot_t * 3).apply_translation([0, 0, bot_t / 2]) or hole(6.0, bot_t * 3)
    )

    # Pocket the pitch servo into the wall (servo lies sideways, shaft pokes out -Y)
    pocket = servo_pocket()
    RX(pocket, 90)  # lay it on its side so shaft points +Y / -Y
    # After RX(90), the pocket's original Z axis becomes Y. Shift to embed in wall.
    pocket.apply_translation([0, bot_d / 2 - wall_t / 2 + 5, bot_t + wall_h / 2])
    body = body.difference(pocket)

    return body


# ---------------------------------------------------------------------------
# Part 3: Pitch bracket  (rides on J2 horn, holds BLDC + bearings)
# ---------------------------------------------------------------------------


def make_pitch_bracket():
    """L-shaped bracket. Short face bolts to J2 horn. Long face holds the BLDC
    coaxially, with a 608 bearing on each side for radial support of the swing arm.
    The swing arm sits OUTSIDE the bracket; the motor's shaft passes through one
    bearing and drives the arm hub. The other end of the arm hub is supported by
    the second bearing on a stub shaft for stability."""
    face_w = 70.0
    face_h = 50.0
    face_t = 6.0
    back_w = face_w
    back_h = 30.0
    back_t = 6.0

    face = box((face_w, face_t, face_h))
    face.apply_translation([0, 0, face_h / 2])

    back = box((back_w, back_h, back_t))
    back.apply_translation([0, back_h / 2 + face_t / 2, back_t / 2])

    body = face.union(back)

    # Back plate: 4-hole horn pattern for bolting to J2 horn
    for ang in (0, 90, 180, 270):
        r = 7.0
        h = hole(M3_CLEAR, back_t * 3)
        h.apply_translation([r * np.cos(np.radians(ang)), back_h / 2 + face_t / 2, back_t / 2])
        body = body.difference(h)
    # Center shaft clearance through back plate
    c = hole(6.0, back_t * 3)
    c.apply_translation([0, back_h / 2 + face_t / 2, back_t / 2])
    body = body.difference(c)

    # Bearing pocket on the face — the bearing's outer race press-fits here.
    # Pocket axis is along +Y (perpendicular to face).
    bp_outer = cylinder(radius=BEARING_OD / 2 + 0.2, height=BEARING_THICK + 0.4, sections=64)
    RX(bp_outer, 90)
    bp_outer.apply_translation([0, face_t / 2 - BEARING_THICK / 2 - 0.2, face_h / 2])
    body = body.difference(bp_outer)

    # Through-hole for shaft + BLDC body clearance (the BLDC body sits behind the face)
    through = cylinder(radius=BLDC_SHAFT_D / 2 + 1.0, height=face_t * 4, sections=48)
    RX(through, 90)
    through.apply_translation([0, 0, face_h / 2])
    body = body.difference(through)

    # BLDC mount screw circle (4 screws on the back side of the face, into the motor)
    # These screws come through the face from the -Y side into motor face.
    r = BLDC_MOUNT_BOLT_CIRCLE / 2
    for ang in (45, 135, 225, 315):
        h = cylinder(radius=BLDC_MOUNT_SCREW_D / 2, height=face_t * 3, sections=24)
        RX(h, 90)
        h.apply_translation(
            [r * np.cos(np.radians(ang)), 0, face_h / 2 + r * np.sin(np.radians(ang))]
        )
        body = body.difference(h)

    return body


# ---------------------------------------------------------------------------
# Part 4: Swing arm  (bolts to BLDC shaft, holds paddle clamp at the end)
# ---------------------------------------------------------------------------


def make_swing_arm():
    """A flat blade arm with a hub at one end (for the BLDC shaft + set screw)
    and a pair of paddle clamp screw bosses at the other end."""
    # Hub end
    hub_r = 14.0
    hub_h = SWING_ARM_T + 6.0
    hub = cylinder(radius=hub_r, height=hub_h, sections=64)
    hub.apply_translation([0, 0, hub_h / 2])

    # Arm shaft
    arm = box((SWING_ARM_W, SWING_ARM_LEN, SWING_ARM_T))
    arm.apply_translation([0, SWING_ARM_LEN / 2, SWING_ARM_T / 2])

    # Tip pad (where the paddle clamp mounts)
    tip_w = 35.0
    tip_d = 35.0
    tip_t = SWING_ARM_T + 2.0
    tip = box((tip_w, tip_d, tip_t))
    tip.apply_translation([0, SWING_ARM_LEN, tip_t / 2])

    body = hub.union(arm).union(tip)

    # Hub: shaft hole + radial set-screw
    shaft = hole(BLDC_SHAFT_D + 0.2, hub_h * 3)
    body = body.difference(shaft)
    set_screw = cylinder(radius=M3_TAP / 2, height=hub_r * 3, sections=24)
    RY(set_screw, 90)
    set_screw.apply_translation([0, 0, hub_h / 2])
    body = body.difference(set_screw)

    # Tip: 4 M3 holes for paddle clamp
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = hole(M3_CLEAR, tip_t * 3)
            h.apply_translation([sx * 10, SWING_ARM_LEN + sy * 10, tip_t / 2])
            body = body.difference(h)

    # Lightening pockets to reduce inertia (the arm whips, mass at the tip hurts)
    n_pockets = 4
    pocket_w = SWING_ARM_W - 8
    spacing = (SWING_ARM_LEN - 60) / n_pockets
    for i in range(n_pockets):
        pocket_y = 30 + i * spacing + spacing / 2
        p = box((pocket_w, spacing * 0.6, SWING_ARM_T * 3))
        p.apply_translation([0, pocket_y, SWING_ARM_T / 2])
        body = body.difference(p)

    return body


# ---------------------------------------------------------------------------
# Part 5: Paddle clamp (two halves — print one, mirror in slicer for the other)
# ---------------------------------------------------------------------------


def make_paddle_clamp_half():
    """One half of the paddle clamp. Two halves bolt through the swing arm tip
    and squeeze the paddle blade between them."""
    w = 35.0
    d = PADDLE_CLAMP_DEPTH + 10
    t = 8.0

    body = box((w, d, t))
    body.apply_translation([0, 0, t / 2])

    # Channel for the paddle blade — half-depth on each clamp half
    chan = box((PADDLE_BLADE_W, PADDLE_CLAMP_DEPTH, PADDLE_BLADE_T / 2 + 0.5))
    # Run the channel along the width; we model "width" as X here.
    # The channel cuts into the +Z face, so it's offset upward.
    chan.apply_translation([0, 0, t - (PADDLE_BLADE_T / 4 + 0.25)])
    # But PADDLE_BLADE_W > w, so it'll exceed the part in X. That's fine — only
    # the intersection inside `body` matters for the subtraction.
    body = body.difference(chan)

    # 4 bolt holes matching the swing arm tip pattern
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = hole(M3_CLEAR, t * 3)
            h.apply_translation([sx * 10, sy * 10, t / 2])
            body = body.difference(h)

    return body


# ---------------------------------------------------------------------------
# Build everything
# ---------------------------------------------------------------------------

PARTS = [
    ("01_base_plate.stl", make_base_plate),
    ("02_yaw_bracket.stl", make_yaw_bracket),
    ("03_pitch_bracket.stl", make_pitch_bracket),
    ("04_swing_arm.stl", make_swing_arm),
    ("05_paddle_clamp.stl", make_paddle_clamp_half),
]


def main():
    for fname, fn in PARTS:
        print(f"Building {fname} ...")
        m = fn()
        # Basic sanity: ensure watertight-ish before export
        print(f"  volume_ok={m.is_volume}  verts={len(m.vertices)}  faces={len(m.faces)}")
        out = os.path.join(HERE, fname)
        m.export(out)
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
