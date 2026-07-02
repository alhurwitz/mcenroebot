import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as R

# --- funnel sized to 90 mm throat (ball 40 + pan/tilt swing + margin), flaring to 116 front ---
# profile (radius, z): z=0 torso/flange back, funnel exits at +z (outside)
prof = np.array(
    [
        (45, 0),
        (45, 4),  # bore through flange (r45 = 90 mm throat)
        (58, 36),  # bore flares to 116 mm at front
        (62, 36),  # front rim (4 mm wall)
        (49, 4),  # outer cone back
        (75, 4),
        (75, 0),  # flange (OD 150)
        (45, 0),
    ]
)  # close
funnel = trimesh.creation.revolve(prof, sections=96)
funnel.merge_vertices()
for fn in (trimesh.repair.fix_winding, trimesh.repair.fix_inversion, trimesh.repair.fix_normals):
    fn(funnel)
print("funnel solid:", funnel.is_volume)

# --- lower lip: tilted scoop tongue at the bottom-front, projecting out + down ---
lip = trimesh.creation.box(extents=[90, 4, 40])
lip.apply_transform(R(np.radians(32), [1, 0, 0]))  # tip the far end downward
lip.apply_translation([0, -60, 40])  # bottom (-Y) of the front opening
body = trimesh.boolean.union([funnel, lip])
# trim anything the lip pokes into the bore (keep throat clear)
clear = trimesh.creation.cylinder(radius=44, height=120)
clear.apply_translation([0, 0, 20])
# (don't subtract full clear -- it would cut the bore wall; only trim lip overlap inside bore)
body.merge_vertices()
trimesh.repair.fix_normals(body)

# --- 4x M3 mounting holes in the flange (avoid the bottom lip) ---
holes = []
for a in (45, 135, 225, 315):
    th = np.radians(a)
    h = trimesh.creation.cylinder(radius=1.7, height=10)
    h.apply_translation([62 * np.cos(th), 62 * np.sin(th), 2])
    holes.append(h)
port = body.difference(trimesh.util.concatenate(holes))
port.merge_vertices()
trimesh.repair.fix_normals(port)

port.export("stomach_port_ring.stl")
rt = trimesh.load("stomach_port_ring.stl")
rt.merge_vertices()
d = port.bounds[1] - port.bounds[0]
print(
    "port volume=",
    rt.is_volume,
    " watertight=",
    rt.is_watertight,
    f" bbox {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f}",
)
print(f"throat 90mm ({90 / 25.4:.1f}in) -> front 116mm ({116 / 25.4:.1f}in), flange OD150, 4x M3")
