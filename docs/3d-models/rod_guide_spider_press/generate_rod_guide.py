import numpy as np
import trimesh

TUBE_ID = 98.0
TUBE_OD = 104.0
RING_OD = 97.6  # 0.2 mm interference into the tube -> snug press
RING_WALL = 3.0
RING_H = 12.0
LIP_OD = 102.0
LIP_H = 2.0
HUB_OD = 28.0
BRG_OD = 22.2  # 608ZZ is 22.0 -> 0.2 slip; tighten to 21.9 if you want press
BRG_W = 7.0
ROD_BORE = 8.5
SPOKE_W = 6.0
SPOKE_H = 5.0
N_SPOKES = 3

r_ring_o = RING_OD / 2
r_ring_i = RING_OD / 2 - RING_WALL
parts = []

# locating ring
ring = trimesh.creation.annulus(r_min=r_ring_i, r_max=r_ring_o, height=RING_H)
ring.apply_translation([0, 0, RING_H / 2])
parts.append(ring)
# anti-push-through lip at top
lip = trimesh.creation.annulus(r_min=r_ring_i, r_max=LIP_OD / 2, height=LIP_H)
lip.apply_translation([0, 0, RING_H - LIP_H / 2])
parts.append(lip)
# central hub (solid, bored later)
hub = trimesh.creation.cylinder(radius=HUB_OD / 2, height=RING_H)
hub.apply_translation([0, 0, RING_H / 2])
parts.append(hub)
# spokes on the plate side (z 0..SPOKE_H) -> print flat, no bridging
span = r_ring_i - HUB_OD / 2 + 4
for k in range(N_SPOKES):
    bx = trimesh.creation.box(extents=[span, SPOKE_W, SPOKE_H])
    bx.apply_translation([HUB_OD / 2 + span / 2 - 2, 0, SPOKE_H / 2])
    bx.apply_transform(trimesh.transformations.rotation_matrix(2 * np.pi * k / N_SPOKES, [0, 0, 1]))
    parts.append(bx)

body = trimesh.boolean.union(parts)
body.merge_vertices()
trimesh.repair.fix_normals(body)

# bearing pocket (opens at top z=RING_H, 7 mm deep -> seats on a shoulder)
pocket = trimesh.creation.cylinder(radius=BRG_OD / 2, height=BRG_W + 1)
pocket.apply_translation([0, 0, RING_H - (BRG_W) / 2 + 0.5])
# rod clearance all the way through
rod = trimesh.creation.cylinder(radius=ROD_BORE / 2, height=RING_H + 8)
rod.apply_translation([0, 0, (RING_H + 8) / 2 - 4])
guide = body.difference(trimesh.boolean.union([pocket, rod]))
guide.merge_vertices()
trimesh.repair.fix_normals(guide)

guide.export("rod_guide_spider.stl")
rt = trimesh.load("rod_guide_spider.stl")
rt.merge_vertices()
d = guide.bounds[1] - guide.bounds[0]
print(
    "guide volume=",
    rt.is_volume,
    " watertight=",
    rt.is_watertight,
    f" bbox {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f}",
)
print(
    f"ring OD {RING_OD} into tube ID {TUBE_ID} | 608ZZ pocket {BRG_OD}x{BRG_W} | rod bore {ROD_BORE}"
)
