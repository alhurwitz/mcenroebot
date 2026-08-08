#!/usr/bin/env python3
"""Exploded view + a per-part plate so it's obvious this is FIVE prints."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# name -> (colour, explode dz, label)
PARTS = [
    ("hopper_cone_v1", "#5b8fb0", 210, "5  hopper_cone_v1\nprint RIM-DOWN, no supports"),
    ("drum_lid_v1", "#95a5a6", 140, "4  drum_lid_v1\nflat"),
    ("escapement_disk_v1", "#e07a3f", 80, "2  escapement_disk_v1\nflat  <- THE CIRCLE PIECE"),
    ("hopper_base_v1", "#7f8c9b", 0, "1  hopper_base_v1\nflange-down, no supports"),
    ("servo_saddle_v1", "#c0392b", -70, "3  servo_saddle_v1\nflat"),
]


def shade(color, normals, alpha=1.0):
    light = np.array([0.4, -0.7, 0.6])
    light /= np.linalg.norm(light)
    rgb = np.array(matplotlib.colors.to_rgb(color))
    lam = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    return np.column_stack([np.clip(rgb[None, :] * lam[:, None], 0, 1), np.full(len(lam), alpha)])


def exploded():
    fig = plt.figure(figsize=(9, 11))
    ax = fig.add_subplot(111, projection="3d")
    for name, color, dz, label in PARTS:
        m = trimesh.load(f"{name}.stl")
        m.apply_translation([0, 0, dz])
        ax.add_collection3d(
            Poly3DCollection(
                m.triangles, facecolors=shade(color, m.face_normals), linewidths=0, zsort="average"
            )
        )
        c = m.bounds.mean(axis=0)
        ax.text(
            c[0] - 165, c[1], m.bounds[1][2] - 12, label, fontsize=8.5, color="#111", ha="left"
        )
    ax.set_xlim(-210, 70)
    ax.set_ylim(-140, 140)
    ax.set_zlim(-80, 500)
    ax.set_box_aspect((280, 280, 580))
    ax.view_init(elev=14, azim=-126)
    ax.set_axis_off()
    ax.set_title("hopper_escapement_v1 — FIVE separate prints (exploded)", fontsize=12)
    fig.savefig("preview_exploded.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def plate():
    """Each part alone, in roughly its print orientation, with its size."""
    fig, axes = plt.subplots(1, 5, figsize=(20, 5), subplot_kw={"projection": "3d"})
    for ax, (name, color, _, label) in zip(axes, PARTS):
        m = trimesh.load(f"{name}.stl")
        if name == "hopper_cone_v1":  # print inverted
            m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        m.apply_translation(-m.bounds.mean(axis=0))
        ax.add_collection3d(
            Poly3DCollection(
                m.triangles, facecolors=shade(color, m.face_normals), linewidths=0, zsort="average"
            )
        )
        r = float(np.abs(m.bounds).max()) * 1.1
        ax.set_xlim(-r, r)
        ax.set_ylim(-r, r)
        ax.set_zlim(-r, r)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=22, azim=-60)
        ax.set_axis_off()
        e = m.extents
        ax.set_title(
            f"{label}\nØ/xy {e[0]:.0f}×{e[1]:.0f} × h{e[2]:.0f} mm   {m.volume / 1000:.0f} cm³",
            fontsize=8.5,
        )
    fig.suptitle("hopper_escapement_v1 — print plate (each part shown in print orientation)", fontsize=12)
    fig.savefig("preview_plate.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    exploded()
    plate()
    print("wrote preview_exploded.png, preview_plate.png")
