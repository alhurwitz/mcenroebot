import numpy as np
import trimesh

PITCH = 50.0
TURNS = 3.0
SEG_H = PITCH * TURNS  # 150 mm
OD = 97.2
CORE = 12.0
FLIGHT_T = 3.0
BORE = 8.5
PEG_R = 44.0
PEG_D = 4.0
PEG_H = 3.5
HOLE_D = 4.4
HOLE_DEPTH = 4.0


def station(t):
    z = SEG_H * t
    a = 2 * np.pi * TURNS * t
    c, s = np.cos(a), np.sin(a)
    ri = CORE / 2 - 0.5
    ro = OD / 2
    return np.array(
        [
            [ri * c, ri * s, z],
            [ro * c, ro * s, z],
            [ro * c, ro * s, z + FLIGHT_T],
            [ri * c, ri * s, z + FLIGHT_T],
        ]
    )


# flight, generated past both ends so the clip leaves clean flush faces at z=0 and z=SEG_H
n = int(TURNS * 72)
ext = 0.05
step = (1 + 2 * ext) / n
parts = [
    trimesh.Trimesh(
        vertices=np.vstack([station(-ext + i * step), station(-ext + i * step + 1.5 * step)])
    ).convex_hull
    for i in range(n)
]
core = trimesh.creation.cylinder(radius=CORE / 2, height=SEG_H + 20)
core.apply_translation([0, 0, SEG_H / 2])
parts.append(core)
body = trimesh.boolean.union(parts)
body.merge_vertices()

# clip flush top and bottom -> end faces are flight cross-sections at angle 0 (continuous when stacked)
big = 200
lo = trimesh.creation.box(extents=[big, big, big])
lo.apply_translation([0, 0, -big / 2])
hi = trimesh.creation.box(extents=[big, big, big])
hi.apply_translation([0, 0, SEG_H + big / 2])
body = body.difference(trimesh.boolean.union([lo, hi]))

# rod bore
bore = trimesh.creation.cylinder(radius=BORE / 2, height=SEG_H + 20)
bore.apply_translation([0, 0, SEG_H / 2])
body = body.difference(bore)

# clocking: peg up from top flight face, matching hole in bottom flight face, both at angle 0
peg = trimesh.creation.cylinder(radius=PEG_D / 2, height=PEG_H)
peg.apply_translation([PEG_R, 0, SEG_H + PEG_H / 2])
body = body.union(peg)
hole = trimesh.creation.cylinder(radius=HOLE_D / 2, height=HOLE_DEPTH + 1)
hole.apply_translation([PEG_R, 0, (HOLE_DEPTH - 1) / 2])
body = body.difference(hole)

body.merge_vertices()
trimesh.repair.fix_normals(body)
body.export("screw_segment_3turn.stl")
rt = trimesh.load("screw_segment_3turn.stl")
rt.merge_vertices()
d = body.bounds[1] - body.bounds[0]
print(
    "screw seg volume=",
    rt.is_volume,
    " watertight=",
    rt.is_watertight,
    f" bbox {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f}",
)
print(f"{TURNS:.0f} turns, {SEG_H:.0f}mm ({SEG_H / 25.4:.1f}in), peg+hole clocking, M8 bore")
