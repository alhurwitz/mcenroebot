#!/usr/bin/env python3
"""Previews for hopper_escapement_v1: shaded iso + a ball-path section."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from generate_parts import BALL, CHUTE_AX, CONE_AX, DISK_AX, FLOOR_Z1, R_P

PARTS = {
    "hopper_base_v1": ("#7f8c9b", 1.0),
    "escapement_disk_v1": ("#e07a3f", 1.0),
    "servo_saddle_v1": ("#c0392b", 1.0),
    "drum_lid_v1": ("#95a5a6", 1.0),
    "hopper_cone_v1": ("#5b8fb0", 0.55),
}


def shade(color, normals, alpha):
    light = np.array([0.4, -0.7, 0.6])
    light /= np.linalg.norm(light)
    rgb = np.array(matplotlib.colors.to_rgb(color))
    lam = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    face = np.clip(rgb[None, :] * lam[:, None], 0, 1)
    return np.column_stack([face, np.full(len(face), alpha)])


def iso():
    fig = plt.figure(figsize=(9, 10))
    ax = fig.add_subplot(111, projection="3d")
    for name, (color, alpha) in PARTS.items():
        m = trimesh.load(f"{name}.stl")
        tris = m.triangles
        ax.add_collection3d(
            Poly3DCollection(
                tris,
                facecolors=shade(color, m.face_normals, alpha),
                linewidths=0,
                zsort="average",
            )
        )
    ax.set_xlim(-200, 60)
    ax.set_ylim(-130, 130)
    ax.set_zlim(0, 290)
    ax.set_box_aspect((260, 260, 290))
    ax.view_init(elev=18, azim=-128)
    ax.set_axis_off()
    ax.set_title(
        "hopper_escapement_v1 — cone + rotary disk, bolted to the launcher chute\n"
        "(+X = fire direction, right)",
        fontsize=11,
    )
    fig.savefig("preview_iso.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def section():
    """Vertical slice through the chute axis AND the cone axis: the ball path."""
    v = CHUTE_AX - CONE_AX  # +s = fire direction (cone sits at -s, as in the launcher frame)
    v = v / np.linalg.norm(v)
    n = np.array([-v[1], v[0], 0.0])  # plane normal
    fig, ax = plt.subplots(figsize=(9, 9))
    for name, (color, _) in PARTS.items():
        m = trimesh.load(f"{name}.stl")
        sec = m.section(plane_origin=[0, 0, 0], plane_normal=n)
        if sec is None:
            continue
        for ent in sec.entities:
            pts = sec.vertices[ent.points]
            s = pts[:, :2] @ v  # distance along the chute->cone direction
            ax.plot(s, pts[:, 2], color=color, lw=1.4)

    # balls
    load_s = float(CONE_AX @ v)
    ax.add_patch(Circle((load_s, FLOOR_Z1 + BALL / 2), BALL / 2, fc="#f1c40f", ec="k", lw=0.8))
    ax.add_patch(Circle((0, FLOOR_Z1 + BALL / 2), BALL / 2, fc="#f1c40f", ec="k", lw=0.8, alpha=0.35))
    ax.annotate(
        "", xy=(0, 8), xytext=(0, FLOOR_Z1 - 4),
        arrowprops=dict(arrowstyle="-|>", color="k", lw=1.8),
    )
    ax.text(load_s, 122, "LOAD\npocket under the cone outlet", ha="center", fontsize=8)
    ax.text(-6, 24, "DISCH\n→ launcher chute", ha="right", fontsize=8)
    ax.text(float(DISK_AX @ v), 34, f"servo / disk axis  (R_P={R_P:.0f})", ha="center", fontsize=8)
    ax.axhline(0, color="k", lw=0.8, ls="--")
    ax.text(58, -12, "launcher chute flange  (z=0)", fontsize=7, ha="right")
    ax.text(58, 250, "fire →", fontsize=9, ha="right")
    ax.set_aspect("equal")
    ax.set_xlim(-160, 60)
    ax.set_ylim(-30, 290)
    ax.set_xlabel("mm along the cone-axis → chute-axis direction")
    ax.set_ylabel("mm above the launcher flange")
    ax.set_title("hopper_escapement_v1 — ball path section", fontsize=11)
    ax.grid(alpha=0.25)
    fig.savefig("preview_section.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    iso()
    section()
    print("wrote preview_iso.png, preview_section.png")
