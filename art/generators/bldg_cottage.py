"""Wurzelheim cottage generator (Spirit Village).

Builds ``bldg_cottage``: a round cream plaster cottage with a domed
terracotta shingle roof, an arched plank door with an iron ring, a round
cross-barred window, a wall lantern on an iron bracket and two stone steps
(art/PIPELINE.md, section 4a; reference ``mockup.png``, top left).

Conventions
-----------
* **Z-up** in Blender, ground contact at ``z = 0``, 1 unit = 1 m, origin at
  the centre of the footprint.
* The door **faces -Y** in Blender, which the glTF exporter maps to glTF
  **+Z** (asset front, Godot ``Vector3.MODEL_FRONT``). Every run checks this
  in the exported GLB.
* Azimuths are measured around the wall from the front (0) towards +X
  (the viewer's right when looking at the door).
* Every size in CONFIG is a full extent (diameter / width / height).
  Door, frame and window are laid out in wall coordinates (``u`` = arc length
  along the wall, ``v`` = height, ``depth`` = distance in front of the plaster)
  and wrapped onto the curved wall by ``wall_point()``.
* Movable parts are their own nodes: ``Door`` (origin on the hinge line, so
  it can swing about the vertical axis), ``Lantern`` with the empty
  ``LanternLight`` at the glass centre (anchor for a light in Godot).

Environment and scene assumption
--------------------------------
Same as ``garden_wight.py``: the modelling code needs Blender's Python
(verified with Blender 5.2.1 LTS), the pure geometry helpers
(``derive_dimensions``, ``roof_rows``, ``step_stones``, ``inspect_glb``) import
without ``bpy``. ``clear_scene()`` wipes the scene, so only run this in its
own ``--background --factory-startup`` process.

Usage (arguments after ``--``)
------------------------------
    blender --background --factory-startup --python-exit-code 1 --python \\
        art/generators/bldg_cottage.py -- \\
        --output-dir build/buildings/bldg_cottage [--render | --views]

The run fails (exit 1 with ``--python-exit-code 1``) when an automatic check
fails: triangle budget, ground contact, node scale, part intersections, door
direction in the GLB. All files are written before that.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import struct
import sys
from pathlib import Path

try:  # Blender-only modules - see "Environment" above.
    import bpy
    import bmesh
    from mathutils import Matrix, Vector
except ImportError:  # pragma: no cover - outside Blender
    bpy = None
    bmesh = None
    Matrix = None
    Vector = None


# ---------------------------------------------------------------------------
# Configuration - the single place to tune the cottage.
# Metres; full extents; azimuths in degrees from the front towards +X.
# ---------------------------------------------------------------------------

CONFIG = {
    # Walls: round plaster drum, slightly flared at the foot.
    "wall_diameter": 2.6,          # at the top of the wall
    "wall_height": 1.8,            # ground to where the roof sits on the wall
    "wall_base_flare": 0.05,       # extra diameter (fraction) at ground level
    "wall_segments": 64,
    "wall_rows": 4,
    # Stone plinth ring around the foot of the wall.
    "base_height": 0.13,
    "base_protrusion": 0.07,       # how far the plinth stands out of the wall
    "base_stones": 16,             # V-notches between stones; must divide base_segments
    "base_notch_depth": 0.03,
    "base_segments": 64,
    # Roof: overhanging dome of shingle rings with rounded tile tongues.
    # The 50 degree game camera looks over the eave: the door crown stays visible
    # only while the eave hangs higher than about overhang * tan(50 deg) above it.
    "roof_eave_diameter": 3.0,     # dome base, without the shingle lip
    "roof_eave_drop": 0.03,        # dome base sits this far below the wall top
    "roof_eave_slope_deg": 22.0,   # dome parameter at the eave: 0 = vertical skirt, higher = flatter eave
    "roof_height": 1.0,            # dome base to apex
    "roof_shape_exponent": 2.0,    # superellipse: 2 = ellipse, higher = fuller shoulder
    "roof_rings": 7,
    "roof_cap_fraction": 0.1,      # share of the profile length kept as a smooth top cap
    "roof_lip": 0.07,              # each ring's lower edge stands out this far (at a tile centre)
    "roof_tile_bulge": 0.7,        # share of the lip lost towards the joints -> visible single tiles
    "roof_tuck": 0.04,             # the next ring starts this far up under the lip
    "roof_tile_width": 0.38,       # target tile width along a ring's lower edge
    "roof_scallop": 0.05,          # tile tongues hang this far below the joints
    "roof_eave_thickness": 0.06,
    "roof_segments": 96,
    # Arched plank door towards the front.
    "door_width": 0.8,             # visible leaf width
    "door_height": 1.15,           # visible sill to arch crown
    "door_arch_rise": 0.4,         # = door_width / 2 -> round arch
    "door_planks": 5,
    "door_plank_gap": 0.016,
    "door_proud": 0.025,           # plank faces in front of the plaster
    "door_embed": 0.04,            # leaf reaches this far behind the plaster
    "door_backing_recess": 0.012,  # dark backing between the planks sits this far behind them
    "door_ring_diameter": 0.13,
    "door_ring_tube": 0.02,
    "door_ring_height": 0.58,      # stud above the sill
    "door_ring_offset": 0.2,       # from the door centre towards the latch side (+X)
    "door_sill_gap": 0.006,        # air between upper step and door/frame
    # Wooden frame around the door opening.
    "frame_width": 0.09,
    "frame_proud": 0.075,
    "frame_lip": 0.03,             # inner lip in front of the leaf edge (hides it)
    "frame_arch_samples": 18,
    # Round window with a cross (viewer's left).
    "window_azimuth_deg": -42.0,
    "window_center_height": 0.92,
    "window_opening_diameter": 0.38,  # visible glass
    "window_frame_width": 0.075,
    "window_frame_proud": 0.07,
    "window_lip": 0.025,
    "window_mullion_width": 0.04,
    "window_mullion_proud": 0.035,
    "window_samples": 32,
    # Wall lantern on an iron bracket (viewer's right).
    "lantern_azimuth_deg": 38.0,
    "lantern_mount_height": 1.3,
    "lantern_arm_length": 0.27,
    "lantern_arm_thickness": 0.03,
    "lantern_glass": (0.12, 0.12, 0.15),   # x, y, z
    "lantern_post": 0.02,
    "lantern_cap_height": 0.08,
    # Stone steps in front of the door (index 0 = lowest, outermost).
    "step_rise": 0.09,
    "step_depth": 0.3,
    "step_widths": (1.3, 1.05),
    "step_stone_splits": ((0.3, 0.38, 0.32), (0.55, 0.45)),  # fractions of the step width
    "step_gap": 0.015,
    "step_bury": 0.16,             # upper step reaches this far into the wall
    "step_tuck": 0.06,             # lower steps reach this far under the step above
    "step_bevel": 0.03,
    "step_height_jitter": 0.02,    # stones only sink, never rise towards the door
    "step_front_jitter": 0.03,
    "step_yaw_jitter_deg": 7.0,
    # Mesh budget and shading.
    "triangle_budget": 8000,       # art/PIPELINE.md section 7
    "smooth_angle_deg": 45.0,      # edges sharper than this stay crisp
    # Preview and check renders (never exported).
    "preview_pitch_deg": 50.0,
    "preview_distance": 14.0,      # orthographic: clipping only
    "preview_margin": 1.08,
    "preview_resolution": (1024, 1024),
    "preview_samples": 64,
    "views_samples": 32,
    "views_side_pitch_deg": 20.0,
    # Light as in game/scenes/garden.tscn (Sun rotation -50/-40 deg, ambient 0.6).
    "sun_direction": (0.413, 0.492, -0.766),  # travel direction, Blender axes
    "sun_strength": 3.5,
    "sun_angle_deg": 12.0,
    "world_color": (0.94, 0.90, 0.82, 1.0),
    "world_strength": 0.3,
    # Game-size comparison: S1 camera shows 18 m of height on 800 logical px.
    "game_px_per_m": 800.0 / 18.0,
    "game_view_size": (4.6, 5.0),         # visible area in metres (camera plane)
    "game_view_target": (0.35, -0.7, 1.0),
    "game_view_scales": (1, 3),           # 1 = logical px, 3 = typical 1080 px wide phone
    "compare_glb": "build/characters/garden_wight/garden_wight.glb",
    "compare_position": (1.15, -2.05),
    # Colours (matte, texture-free) as sRGB, like a colour picker or Godot's
    # albedo_color; converted to linear for Blender and the GLB.
    "colors": {
        "plaster_cream": (0.93, 0.88, 0.78, 1.0),
        "roof_terracotta": (0.68, 0.33, 0.22, 1.0),
        "roof_terracotta_alt": (0.74, 0.39, 0.26, 1.0),
        "roof_underside": (0.36, 0.17, 0.11, 1.0),
        "wood_door": (0.56, 0.37, 0.22, 1.0),
        "wood_dark": (0.24, 0.15, 0.09, 1.0),
        "wood_frame": (0.43, 0.28, 0.17, 1.0),
        "iron": (0.17, 0.17, 0.18, 1.0),
        "window_glass": (0.20, 0.24, 0.26, 1.0),
        "lantern_glow": (1.0, 0.86, 0.56, 1.0),
        "stone": (0.64, 0.61, 0.56, 1.0),
        "stone_base": (0.56, 0.53, 0.49, 1.0),
        "preview_ground": (0.42, 0.30, 0.20, 1.0),  # ground in game/scenes/garden.tscn
    },
}

ASSET_NAME = "bldg_cottage"
COLLECTION_NAME = "Cottage_Building"
PREVIEW_COLLECTION_NAME = "Cottage_PreviewSetup"
ROOT_NAME = "Cottage_Root"
BLENDER_API_TARGET = "5.2.1 LTS (verified); older versions untested"

# The door faces -Y; preview cameras orbit from that side.
FRONT_SIGN = -1.0

# Parts that must not interpenetrate. Everything may sink into the walls,
# steps may sink into the plinth, the roof sits on the walls.
SEPARATE_PARTS = (
    ("Door", "DoorFrame"), ("Door", "Steps"), ("Door", "Roof"), ("Door", "Base"),
    ("DoorFrame", "Roof"), ("DoorFrame", "Steps"), ("DoorFrame", "Window"),
    ("Window", "Roof"), ("Window", "Base"), ("Window", "Steps"),
    ("Lantern", "Roof"), ("Lantern", "DoorFrame"), ("Lantern", "Door"), ("Lantern", "Window"),
    ("Steps", "Roof"),
)

# Roof material slots.
ROOF_MAT_A, ROOF_MAT_B, ROOF_MAT_UNDER = 0, 1, 2


# ---------------------------------------------------------------------------
# Pure geometry - no bpy, so these can be checked outside Blender.
# ---------------------------------------------------------------------------

def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    x = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def srgb_to_linear(rgba) -> tuple:
    """sRGB colour (0..1) -> linear, alpha unchanged."""
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(channel(c) for c in rgba[:3]) + tuple(rgba[3:])


def _hash01(*keys: float) -> float:
    """Deterministic pseudo-random value in [0, 1) - stable across runs."""
    x = math.sin(sum((i + 1) * 12.9898 * k + 78.233 * (i + 1) for i, k in enumerate(keys))) * 43758.5453
    return x - math.floor(x)


def wall_radius_at(z: float, config: dict) -> float:
    """Plaster surface radius at height ``z`` (flared towards the ground)."""
    t = min(max(z / config["wall_height"], 0.0), 1.0)
    return config["wall_diameter"] / 2.0 * (1.0 + config["wall_base_flare"] * (1.0 - t) ** 2)


def wall_point(azimuth: float, u: float, v: float, depth: float, config: dict, ref_radius: float) -> tuple:
    """Wall coordinates -> world point.

    ``u`` is arc length at ``ref_radius`` (positive towards +X seen from the
    front), ``v`` the height, ``depth`` the distance in front of the plaster.
    """
    theta = azimuth + u / ref_radius
    r = wall_radius_at(v, config) + depth
    return (r * math.sin(theta), FRONT_SIGN * r * math.cos(theta), v)


def wall_outward(azimuth: float) -> tuple:
    return (math.sin(azimuth), FRONT_SIGN * math.cos(azimuth), 0.0)


def _roof_profile(config: dict, eave_radius: float, eave_z: float, samples: int = 400) -> list:
    """Dome profile from apex to eave as (arc_length, r, z).

    A superellipse quarter, cut at ``roof_eave_slope_deg`` so the eave is not a
    vertical skirt; scaled so the cut passes through the eave point.
    """
    exponent = 2.0 / config["roof_shape_exponent"]
    alpha0 = math.radians(config["roof_eave_slope_deg"])
    radius_scale = eave_radius / math.cos(alpha0) ** exponent
    height_scale = config["roof_height"] / (1.0 - math.sin(alpha0) ** exponent)
    top_z = eave_z + config["roof_height"]
    table = []
    length = 0.0
    previous = None
    for i in range(samples + 1):
        alpha = 0.5 * math.pi - (0.5 * math.pi - alpha0) * i / samples
        r = radius_scale * max(math.cos(alpha), 0.0) ** exponent
        z = top_z - height_scale * (1.0 - max(math.sin(alpha), 0.0) ** exponent)
        if previous is not None:
            length += math.hypot(r - previous[0], z - previous[1])
        table.append((length, r, z))
        previous = (r, z)
    return table


def roof_profile_at(table: list, s: float) -> tuple:
    """(r, z, tangent_r, tangent_z) at arc length ``s``; the tangent points down the roof."""
    lengths = [row[0] for row in table]
    s = min(max(s, 0.0), lengths[-1])
    i = min(max(bisect.bisect_left(lengths, s), 1), len(table) - 1)
    s0, r0, z0 = table[i - 1]
    s1, r1, z1 = table[i]
    f = 0.0 if s1 == s0 else (s - s0) / (s1 - s0)
    norm = math.hypot(r1 - r0, z1 - z0) or 1.0
    return (r0 + (r1 - r0) * f, z0 + (z1 - z0) * f, (r1 - r0) / norm, (z1 - z0) / norm)


def derive_dimensions(config: dict) -> dict:
    """Resolve CONFIG into concrete placements (all world space, metres)."""
    d: dict = {}
    wall_h = config["wall_height"]
    d["wall_top_radius"] = config["wall_diameter"] / 2.0
    d["wall_base_radius"] = wall_radius_at(0.0, config)

    n_steps = len(config["step_widths"])
    d["n_steps"] = n_steps
    d["step_top"] = config["step_rise"] * n_steps

    # Door: the frame path (a = 0) lies one lip outside the visible leaf edge;
    # the leaf reaches 70 % under the lip, so its edge stays hidden.
    lip = config["frame_lip"]
    half = config["door_width"] / 2.0
    rise = config["door_arch_rise"]
    d["door_sill"] = d["step_top"] + config["door_sill_gap"]
    d["door_spring"] = d["door_sill"] + config["door_height"] - rise
    d["door_crown"] = d["door_sill"] + config["door_height"]
    d["door_ref_radius"] = wall_radius_at((d["door_sill"] + d["door_crown"]) / 2.0, config)
    d["door_leaf_half"] = half + 0.7 * lip
    d["door_leaf_rise"] = rise + 0.7 * lip
    d["frame_path_half"] = half + lip
    d["frame_path_rise"] = rise + lip
    d["frame_top"] = d["door_spring"] + d["frame_path_rise"] + config["frame_width"]
    d["frame_outer_half"] = d["frame_path_half"] + config["frame_width"]

    # Window.
    wlip = config["window_lip"]
    d["window_azimuth"] = math.radians(config["window_azimuth_deg"])
    d["window_center_z"] = config["window_center_height"]
    d["window_ref_radius"] = wall_radius_at(d["window_center_z"], config)
    d["window_path_radius"] = config["window_opening_diameter"] / 2.0 + wlip
    d["window_glass_radius"] = config["window_opening_diameter"] / 2.0 + 0.7 * wlip
    d["window_outer_radius"] = d["window_path_radius"] + config["window_frame_width"]

    # Lantern.
    d["lantern_azimuth"] = math.radians(config["lantern_azimuth_deg"])
    d["lantern_mount"] = wall_point(d["lantern_azimuth"], 0.0, config["lantern_mount_height"], 0.0,
                                    config, wall_radius_at(config["lantern_mount_height"], config))

    # Roof.
    d["eave_radius"] = config["roof_eave_diameter"] / 2.0
    d["eave_z"] = wall_h - config["roof_eave_drop"]
    d["apex_z"] = d["eave_z"] + config["roof_height"]
    d["roof_profile"] = _roof_profile(config, d["eave_radius"], d["eave_z"])

    d["steps"] = step_stones(config, d)
    d["step_front_distance"] = config["step_depth"] * n_steps + config["step_front_jitter"]

    d["total_height"] = d["apex_z"]
    d["footprint_radius"] = max(
        d["eave_radius"] + config["roof_lip"],
        d["wall_base_radius"] + d["step_front_distance"],
    )
    return d


def step_stones(config: dict, dims: dict) -> list:
    """Stone blocks of the steps: dicts with centre, extents (x, y, z) and yaw."""
    stones = []
    n = dims["n_steps"]
    depth = config["step_depth"]
    base_r = dims["wall_base_radius"]
    for step, (width, splits) in enumerate(zip(config["step_widths"], config["step_stone_splits"])):
        top = config["step_rise"] * (step + 1)
        if step == n - 1:
            dist_back = -config["step_bury"]
        else:
            dist_back = depth * (n - step - 1) - config["step_tuck"]
        x = -width / 2.0
        for j, share in enumerate(splits):
            stone_w = share * width
            dist_front = depth * (n - step) + (_hash01(step, j, 3.0) - 0.5) * config["step_front_jitter"]
            height = top - config["step_height_jitter"] * _hash01(step, j, 1.0)
            yaw = math.radians((_hash01(step, j, 2.0) - 0.5) * 2.0 * config["step_yaw_jitter_deg"])
            stones.append({
                "center": (x + stone_w / 2.0, FRONT_SIGN * (base_r + (dist_front + dist_back) / 2.0), height / 2.0),
                "extents": (stone_w - config["step_gap"], dist_front - dist_back, height),
                "yaw": yaw,
            })
            x += stone_w
    return stones


def roof_rows(config: dict, dims: dict) -> list:
    """Roof as rows of points from apex to the hidden underside centre.

    Returns ``(material_index, points)`` per row; the material belongs to the
    band between the previous row and this one. Rows are single points (apex,
    underside centre) or rings of ``roof_segments`` points.
    """
    segments = config["roof_segments"]
    table = dims["roof_profile"]
    length = table[-1][0]
    s_cap = length * config["roof_cap_fraction"]
    rings = config["roof_rings"]
    band = (length - s_cap) / rings
    lip = config["roof_lip"]
    scallop = config["roof_scallop"]
    bulge = config["roof_tile_bulge"]

    def ring(s, lip_share, drop_share, tiles=1, phase=0.0):
        r, z, tr, tz = roof_profile_at(table, s)
        nr, nz = -tz, tr  # outward normal of the downward tangent
        points = []
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            tongue = abs(math.sin(tiles * phi / 2.0 + phase)) ** 0.7 if drop_share else 0.0
            drop = scallop * drop_share * tongue
            out = lip * lip_share * (1.0 - bulge * (1.0 - tongue))
            rr = r + nr * out + tr * drop
            zz = z + nz * out + tz * drop
            points.append((rr * math.sin(phi), FRONT_SIGN * rr * math.cos(phi), zz))
        return points

    apex_r, apex_z, _, _ = roof_profile_at(table, 0.0)
    rows = [(ROOF_MAT_A, [(0.0, 0.0, apex_z)])]
    # Support rings; the last one sits close to the first tile row, so the
    # grooved tile normals do not streak across the smooth cap.
    for share in (0.5, 0.9, 1.0):
        rows.append((ROOF_MAT_A, ring(s_cap * share, 0.0, 0.0)))
    for k in range(rings):
        s_top = s_cap + k * band
        s_bottom = s_top + band
        r_bottom = roof_profile_at(table, s_bottom)[0]
        tiles = max(5, round(2.0 * math.pi * r_bottom / config["roof_tile_width"]))
        phase = 0.5 * math.pi * (k % 2)
        material = ROOF_MAT_A if k % 2 == 0 else ROOF_MAT_B
        if k > 0:  # back up under the previous ring's lip
            rows.append((ROOF_MAT_UNDER, ring(s_top - config["roof_tuck"], 0.0, 0.0)))
        rows.append((material, ring(s_bottom, 1.0, 1.0, tiles, phase)))

    # Eave underside, then a flat disc hidden inside the wall top.
    under_z = config["wall_height"] - 0.06
    for r, z in (
        (dims["eave_radius"] - 0.02, dims["eave_z"] + config["roof_eave_thickness"]),
        (dims["wall_top_radius"] - 0.08, under_z),
    ):
        rows.append((ROOF_MAT_UNDER, [
            (r * math.sin(2.0 * math.pi * j / segments), FRONT_SIGN * r * math.cos(2.0 * math.pi * j / segments), z)
            for j in range(segments)
        ]))
    rows.append((ROOF_MAT_UNDER, [(0.0, 0.0, under_z)]))
    return rows


def door_top(u: float, spring: float, half: float, rise: float) -> float:
    """Height of an arched outline (elliptic top) at ``u``."""
    x = min(abs(u) / half, 1.0)
    return spring + rise * math.sqrt(max(1.0 - x * x, 0.0))


def door_frame_path(config: dict, dims: dict) -> list:
    """Frame centre-line ``(u, v)``, clockwise seen from the front (up left, down right)."""
    half, rise = dims["frame_path_half"], dims["frame_path_rise"]
    sill, spring = dims["door_sill"], dims["door_spring"]
    path = [(-half, sill + (spring - sill) * f) for f in (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)]
    samples = config["frame_arch_samples"]
    for i in range(1, samples):
        phi = math.pi * (1.0 - i / samples)
        path.append((half * math.cos(phi), spring + rise * math.sin(phi)))
    path.extend((half, sill + (spring - sill) * f) for f in (1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0))
    return path


def inspect_glb(path) -> dict:
    """Read a GLB's JSON chunk: node names/transforms, triangles, cameras, lights."""
    data = Path(path).read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{path} is not a GLB file")
    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON":
        raise ValueError(f"{path}: first chunk is not JSON")
    gltf = json.loads(data[20:20 + chunk_length])

    triangles = 0
    for node in gltf.get("nodes", []):
        if "mesh" not in node:
            continue
        for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
            if primitive.get("mode", 4) != 4:
                continue
            accessor = primitive.get("indices", primitive["attributes"]["POSITION"])
            triangles += gltf["accessors"][accessor]["count"] // 3

    nodes = {node.get("name", f"#{i}"): node for i, node in enumerate(gltf.get("nodes", []))}
    return {
        "node_names": sorted(nodes),
        "nodes": nodes,
        "triangles": triangles,
        "materials": len(gltf.get("materials", [])),
        "cameras": len(gltf.get("cameras", [])),
        "lights": len(gltf.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])),
        "scaled_nodes": sorted(
            name for name, node in nodes.items()
            if any(abs(c - 1.0) > 1e-6 for c in node.get("scale", (1.0, 1.0, 1.0)))
        ),
    }


def orbit_camera(target, yaw_deg: float, pitch_deg: float, distance: float) -> tuple:
    """(location, rotation_euler) of a camera looking at ``target``.

    Yaw 0 is the front camera on -Y; positive yaw orbits towards +X.
    """
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    horizontal = (math.sin(yaw), FRONT_SIGN * math.cos(yaw))
    location = (
        target[0] + horizontal[0] * math.cos(pitch) * distance,
        target[1] + horizontal[1] * math.cos(pitch) * distance,
        target[2] + math.sin(pitch) * distance,
    )
    return location, (math.pi / 2.0 - pitch, 0.0, yaw)


def fit_ortho_scale(dims: dict, pitch_deg: float, aspect: float, margin: float) -> float:
    """Vertical ortho extent that shows the whole cottage (square footprint bound)."""
    pitch = math.radians(pitch_deg)
    span = 2.0 * dims["footprint_radius"]
    vertical = dims["total_height"] * math.cos(pitch) + span * math.sin(pitch)
    return max(vertical, span / aspect) * margin


# ---------------------------------------------------------------------------
# Small Blender helpers
# ---------------------------------------------------------------------------

def _link_only(obj, collection) -> None:
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)


def get_or_create_material(name: str, rgba, emission: float = 0.0):
    """Flat, matte Principled BSDF material - no textures."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):  # node materials are the default from 5.0 on
        mat.use_nodes = True
    rgba = srgb_to_linear(rgba)
    mat.diffuse_color = rgba
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.85
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
        if emission > 0.0 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def _materials(config: dict, keys) -> list:
    colors = config["colors"]
    names = {
        "plaster_cream": "Mat_PlasterCream", "roof_terracotta": "Mat_RoofTerracotta",
        "roof_terracotta_alt": "Mat_RoofTerracottaAlt", "roof_underside": "Mat_RoofUnderside",
        "wood_door": "Mat_WoodDoor", "wood_dark": "Mat_WoodDark", "wood_frame": "Mat_WoodFrame",
        "iron": "Mat_Iron", "window_glass": "Mat_WindowGlass", "lantern_glow": "Mat_LanternGlow",
        "stone": "Mat_Stone", "stone_base": "Mat_StoneBase", "preview_ground": "Mat_PreviewGround",
    }
    return [
        get_or_create_material(names[key], colors[key], emission=2.0 if key == "lantern_glow" else 0.0)
        for key in keys
    ]


def clear_scene() -> None:
    """Wipe the factory-startup scene (destructive by design, see module docstring)."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            block.remove(item)


def _object_from_bmesh(name: str, bm, materials, origin=(0.0, 0.0, 0.0), sharp_angle_deg=None):
    """Recalculate normals, move ``origin`` to the object origin, create the object."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, vec=-Vector(origin), verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.shade_smooth()
    if sharp_angle_deg is not None:
        mesh.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))
    for material in materials:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = origin
    return obj


def _bridge_rows(bm, rows, materials, loop: bool = False) -> None:
    """Connect rows of vertices (rings or single points) with quads/triangles.

    ``materials[i]`` is used for the band ending at row ``i``; with ``loop``
    the last row also connects back to the first (closed profile).
    """
    pairs = [(rows[i - 1], rows[i], materials[i]) for i in range(1, len(rows))]
    if loop:
        pairs.append((rows[-1], rows[0], materials[0]))
    for a, b, material in pairs:
        if len(a) == 1:
            faces = [bm.faces.new((a[0], b[j], b[(j + 1) % len(b)])) for j in range(len(b))]
        elif len(b) == 1:
            faces = [bm.faces.new((a[j], a[(j + 1) % len(a)], b[0])) for j in range(len(a))]
        else:
            faces = [bm.faces.new((a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]))
                     for j in range(len(a))]
        for face in faces:
            face.material_index = material


def _ring(radius: float, z: float, segments: int) -> list:
    return [(radius * math.sin(2.0 * math.pi * j / segments),
             FRONT_SIGN * radius * math.cos(2.0 * math.pi * j / segments), z) for j in range(segments)]


def _wall_slab(bm, to3d, u0, u1, v0, top, d_back, d_front, cols, rows, material_index) -> None:
    """Closed slab on the wall: ``u0..u1`` wide, from ``v0`` up to ``top(u)``."""
    front, back = [], []
    for c in range(cols + 1):
        u = u0 + (u1 - u0) * c / cols
        v_top = top(u)
        heights = [v0 + (v_top - v0) * r / rows for r in range(rows + 1)]
        front.append([bm.verts.new(to3d(u, v, d_front)) for v in heights])
        back.append([bm.verts.new(to3d(u, v, d_back)) for v in heights])
    faces = []
    for c in range(cols):
        for r in range(rows):
            faces.append(bm.faces.new((front[c][r], front[c + 1][r], front[c + 1][r + 1], front[c][r + 1])))
            faces.append(bm.faces.new((back[c][r], back[c][r + 1], back[c + 1][r + 1], back[c + 1][r])))
    outline = ([(c, 0) for c in range(cols)] + [(cols, r) for r in range(rows)]
               + [(c, rows) for c in range(cols, 0, -1)] + [(0, r) for r in range(rows, 0, -1)])
    for i, (c, r) in enumerate(outline):
        c2, r2 = outline[(i + 1) % len(outline)]
        faces.append(bm.faces.new((front[c][r], back[c][r], back[c2][r2], front[c2][r2])))
    for face in faces:
        face.material_index = material_index


def _sweep_on_wall(bm, to3d, path, section, closed: bool, material_index) -> None:
    """Sweep a 2D ``section`` of (a, depth) along a clockwise ``path`` of (u, v).

    ``a`` is the in-plane offset away from the enclosed opening.
    """
    count = len(path)
    rings = []
    for i, (u, v) in enumerate(path):
        if closed:
            prev, nxt = path[i - 1], path[(i + 1) % count]
        else:
            prev, nxt = path[max(i - 1, 0)], path[min(i + 1, count - 1)]
        tu, tv = nxt[0] - prev[0], nxt[1] - prev[1]
        length = math.hypot(tu, tv)
        nu, nv = -tv / length, tu / length
        rings.append([bm.verts.new(to3d(u + nu * a, v + nv * a, depth)) for a, depth in section])
    faces = []
    links = list(zip(rings[:-1], rings[1:]))
    if closed:
        links.append((rings[-1], rings[0]))
    m = len(section)
    for a_ring, b_ring in links:
        for j in range(m):
            k = (j + 1) % m
            faces.append(bm.faces.new((a_ring[j], a_ring[k], b_ring[k], b_ring[j])))
    if not closed:
        faces.append(bm.faces.new(rings[0]))
        faces.append(bm.faces.new(list(reversed(rings[-1]))))
    for face in faces:
        face.material_index = material_index


def _add_box(bm, center, extents, material_index, rotation=None) -> list:
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=Vector(extents), verts=verts)
    if rotation is not None:
        bmesh.ops.rotate(bm, cent=Vector((0.0, 0.0, 0.0)), matrix=rotation, verts=verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=verts)
    for face in {f for v in verts for f in v.link_faces}:
        face.material_index = material_index
    return verts


def _box_between(bm, p0, p1, thickness, material_index) -> None:
    """Square-section bar from ``p0`` to ``p1`` (local X stays the bar's width axis)."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0).normalized()
    width_axis = Vector((1.0, 0.0, 0.0))
    third = width_axis.cross(axis).normalized()
    rotation = Matrix((width_axis, axis, third)).transposed()
    _add_box(bm, (p0 + p1) / 2.0, (thickness, (p1 - p0).length, thickness), material_index, rotation)


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def build_walls(config: dict, dims: dict):
    bm = bmesh.new()
    segments, rows = config["wall_segments"], config["wall_rows"]
    heights = [config["wall_height"] * i / rows for i in range(rows + 1)]
    vert_rows = [[bm.verts.new((0.0, 0.0, 0.0))]]
    vert_rows += [[bm.verts.new(p) for p in _ring(wall_radius_at(z, config), z, segments)] for z in heights]
    vert_rows.append([bm.verts.new((0.0, 0.0, config["wall_height"]))])
    _bridge_rows(bm, vert_rows, [0] * len(vert_rows))
    return _object_from_bmesh("Walls", bm, _materials(config, ["plaster_cream"]))


def build_base(config: dict, dims: dict):
    """Stone plinth ring with V-notches between the stones."""
    bm = bmesh.new()
    segments, stones = config["base_segments"], config["base_stones"]
    height, protrusion = config["base_height"], config["base_protrusion"]
    r0, r_top = wall_radius_at(0.0, config), wall_radius_at(height, config)
    # Closed profile (radius, z, stands out -> gets notched).
    profile = (
        (r0 - 0.05, 0.0, False),
        (r0 + protrusion, 0.0, True),
        (r_top + protrusion * 0.85, height * 0.7, True),
        (r_top + protrusion * 0.35, height, True),
        (r_top - 0.05, height, False),
    )
    vert_rows = []
    for radius, z, notched in profile:
        row = []
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            r, zz = radius, z
            if notched:
                joint = 1.0 - abs(math.sin(stones * phi / 2.0)) ** 0.35
                r -= config["base_notch_depth"] * joint
                if z > 0.0:
                    zz -= config["base_notch_depth"] * 0.8 * joint
            row.append(bm.verts.new((r * math.sin(phi), FRONT_SIGN * r * math.cos(phi), zz)))
        vert_rows.append(row)
    _bridge_rows(bm, vert_rows, [0] * len(vert_rows), loop=True)
    return _object_from_bmesh("Base", bm, _materials(config, ["stone_base"]), sharp_angle_deg=config["smooth_angle_deg"])


def build_roof(config: dict, dims: dict):
    bm = bmesh.new()
    rows = roof_rows(config, dims)
    vert_rows = [[bm.verts.new(p) for p in points] for _, points in rows]
    _bridge_rows(bm, vert_rows, [material for material, _ in rows])
    materials = _materials(config, ["roof_terracotta", "roof_terracotta_alt", "roof_underside"])
    return _object_from_bmesh("Roof", bm, materials, origin=(0.0, 0.0, config["wall_height"]),
                              sharp_angle_deg=config["smooth_angle_deg"])


def build_door(config: dict, dims: dict):
    """Plank leaf with dark backing and an iron ring; origin on the hinge line (-X edge)."""
    bm = bmesh.new()
    ref = dims["door_ref_radius"]

    def to3d(u, v, depth):
        return wall_point(0.0, u, v, depth, config, ref)

    half, rise = dims["door_leaf_half"], dims["door_leaf_rise"]
    sill, spring = dims["door_sill"], dims["door_spring"]

    def top(u):
        return door_top(u, spring, half, rise)

    planks, gap = config["door_planks"], config["door_plank_gap"]
    plank_w = (2.0 * half - (planks - 1) * gap) / planks
    for i in range(planks):
        u0 = -half + i * (plank_w + gap)
        _wall_slab(bm, to3d, u0, u0 + plank_w, sill, top, -config["door_embed"], config["door_proud"], 4, 3, 0)
    _wall_slab(bm, to3d, -half, half, sill, top, -config["door_embed"],
               config["door_proud"] - config["door_backing_recess"], 12, 3, 1)

    # Iron ring hanging from a stud, in the plane of the door.
    u_ring = config["door_ring_offset"]
    theta = u_ring / ref
    e_u = Vector((math.cos(theta), math.sin(theta), 0.0))  # along the wall towards +X
    up = Vector((0.0, 0.0, 1.0))
    normal = Vector(wall_outward(theta))
    tube = config["door_ring_tube"]
    major = config["door_ring_diameter"] / 2.0 - tube / 2.0
    stud_v = sill + config["door_ring_height"]
    front = config["door_proud"]
    stud = Vector(to3d(u_ring, stud_v, front))
    _add_box(bm, stud + normal * 0.015, (0.035, 0.03, 0.035), 2,
             Matrix.Rotation(theta, 3, 'Z'))
    center = Vector(to3d(u_ring, stud_v - major, front)) + normal * (tube / 2.0 + 0.004)
    around, section = 16, 6
    torus = []
    for i in range(around):
        a = 2.0 * math.pi * i / around
        radial = e_u * math.cos(a) + up * math.sin(a)
        torus.append([
            bm.verts.new(center + radial * (major + tube / 2.0 * math.cos(b)) + normal * (tube / 2.0 * math.sin(b)))
            for b in (2.0 * math.pi * k / section for k in range(section))
        ])
    for i in range(around):
        ring_a, ring_b = torus[i], torus[(i + 1) % around]
        for k in range(section):
            face = bm.faces.new((ring_a[k], ring_a[(k + 1) % section], ring_b[(k + 1) % section], ring_b[k]))
            face.material_index = 2

    hinge = to3d(-half, sill, front)
    return _object_from_bmesh("Door", bm, _materials(config, ["wood_door", "wood_dark", "iron"]),
                              origin=hinge, sharp_angle_deg=config["smooth_angle_deg"])


def build_door_frame(config: dict, dims: dict):
    bm = bmesh.new()
    ref = dims["door_ref_radius"]
    lip, width = config["frame_lip"], config["frame_width"]
    proud, back = config["frame_proud"], -0.03
    lip_back = config["door_proud"] + 0.012
    chamfer = 0.02
    section = (
        (-lip, lip_back), (-lip, proud), (width - chamfer, proud),
        (width, proud - chamfer), (width, back), (0.0, back), (0.0, lip_back),
    )
    _sweep_on_wall(bm, lambda u, v, depth: wall_point(0.0, u, v, depth, config, ref),
                   door_frame_path(config, dims), section, closed=False, material_index=0)
    origin = wall_point(0.0, 0.0, dims["door_sill"], 0.0, config, ref)
    return _object_from_bmesh("DoorFrame", bm, _materials(config, ["wood_frame"]),
                              origin=origin, sharp_angle_deg=config["smooth_angle_deg"])


def build_window(config: dict, dims: dict):
    bm = bmesh.new()
    azimuth, ref, cz = dims["window_azimuth"], dims["window_ref_radius"], dims["window_center_z"]

    def to3d(u, v, depth):
        return wall_point(azimuth, u, v, depth, config, ref)

    samples = config["window_samples"]
    lip, width = config["window_lip"], config["window_frame_width"]
    proud, back = config["window_frame_proud"], -0.03
    lip_back = config["window_mullion_proud"] + 0.008
    path_r = dims["window_path_radius"]
    path = [(path_r * math.cos(-2.0 * math.pi * i / samples), cz + path_r * math.sin(-2.0 * math.pi * i / samples))
            for i in range(samples)]
    section = ((-lip, lip_back), (-lip, proud), (width, proud), (width, back), (0.0, back), (0.0, lip_back))
    _sweep_on_wall(bm, to3d, path, section, closed=True, material_index=0)

    # Glass: a thin closed disc behind the lip.
    glass_r = dims["window_glass_radius"]
    front_ring, back_ring = [], []
    for i in range(samples):
        phi = 2.0 * math.pi * i / samples
        u, v = glass_r * math.cos(phi), cz + glass_r * math.sin(phi)
        front_ring.append(bm.verts.new(to3d(u, v, 0.004)))
        back_ring.append(bm.verts.new(to3d(u, v, back)))
    glass_faces = [bm.faces.new(front_ring), bm.faces.new(list(reversed(back_ring)))]
    for i in range(samples):
        k = (i + 1) % samples
        glass_faces.append(bm.faces.new((front_ring[i], back_ring[i], back_ring[k], front_ring[k])))
    for face in glass_faces:
        face.material_index = 1

    # Cross bars, ending under the lip.
    half_w = config["window_mullion_width"] / 2.0
    reach = glass_r
    mullion_front = config["window_mullion_proud"]
    _wall_slab(bm, to3d, -half_w, half_w, cz - reach, lambda u: cz + reach, back, mullion_front, 1, 4, 0)
    _wall_slab(bm, to3d, -reach, reach, cz - half_w, lambda u: cz + half_w, back, mullion_front, 4, 1, 0)

    origin = wall_point(azimuth, 0.0, cz, 0.0, config, ref)
    return _object_from_bmesh("Window", bm, _materials(config, ["wood_frame", "window_glass"]),
                              origin=origin, sharp_angle_deg=config["smooth_angle_deg"])


def build_lantern(config: dict, dims: dict) -> list:
    """Bracket + hanging lantern, built in a local frame (-Y = away from the wall).

    Returns the lantern object and its ``LanternLight`` anchor empty.
    """
    bm = bmesh.new()
    arm_len, arm_t = config["lantern_arm_length"], config["lantern_arm_thickness"]
    gx, gy, gz = config["lantern_glass"]
    post = config["lantern_post"]
    arm_z = 0.05
    ly = -arm_len + 0.04  # lantern axis, under the arm's end
    iron, glow = 0, 1

    _add_box(bm, (0.0, 0.0, 0.0), (0.08, 0.04, 0.16), iron)                      # wall plate
    _add_box(bm, (0.0, -arm_len / 2.0, arm_z), (arm_t, arm_len, arm_t), iron)     # arm
    _box_between(bm, (0.0, -0.01, -0.06), (0.0, -arm_len * 0.62, arm_z), 0.022, iron)  # brace

    cap_base = arm_z - arm_t / 2.0 - config["lantern_cap_height"] + 0.01
    cone = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=4,
        radius1=gx * 0.78, radius2=0.0, depth=config["lantern_cap_height"],
    )["verts"]
    bmesh.ops.rotate(bm, cent=Vector((0.0, 0.0, 0.0)), matrix=Matrix.Rotation(math.pi / 4.0, 3, 'Z'), verts=cone)
    bmesh.ops.translate(bm, vec=Vector((0.0, ly, cap_base + config["lantern_cap_height"] / 2.0)), verts=cone)
    for face in {f for v in cone for f in v.link_faces}:
        face.material_index = iron

    rim_z = cap_base - 0.01
    _add_box(bm, (0.0, ly, rim_z), (gx + 0.04, gy + 0.04, 0.02), iron)
    glass_top = rim_z - 0.005
    glass_center_z = glass_top - gz / 2.0
    _add_box(bm, (0.0, ly, glass_center_z), (gx, gy, gz), glow)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _add_box(bm, (sx * gx / 2.0, ly + sy * gy / 2.0, glass_center_z), (post, post, gz), iron)
    bottom_z = glass_top - gz - 0.0075
    _add_box(bm, (0.0, ly, bottom_z), (gx + 0.03, gy + 0.03, 0.025), iron)
    _add_box(bm, (0.0, ly, bottom_z - 0.03), (0.03, 0.03, 0.035), iron)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Lantern")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for material in _materials(config, ["iron", "lantern_glow"]):
        mesh.materials.append(material)
    lantern = bpy.data.objects.new("Lantern", mesh)
    lantern.location = dims["lantern_mount"]
    lantern.rotation_euler = (0.0, 0.0, dims["lantern_azimuth"])

    light = bpy.data.objects.new("LanternLight", None)
    light.empty_display_size = 0.05
    light.location = (0.0, ly, glass_center_z)
    light.parent = lantern
    return [lantern, light]


def build_steps(config: dict, dims: dict):
    bm = bmesh.new()
    for stone in dims["steps"]:
        verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, vec=Vector(stone["extents"]), verts=verts)
        bmesh.ops.rotate(bm, cent=Vector((0.0, 0.0, 0.0)), matrix=Matrix.Rotation(stone["yaw"], 3, 'Z'), verts=verts)
        bmesh.ops.translate(bm, vec=Vector(stone["center"]), verts=verts)
    bmesh.ops.bevel(
        bm, geom=list(bm.verts) + list(bm.edges), offset=config["step_bevel"],
        offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES',
    )
    for face in bm.faces:
        face.material_index = 0
    origin = (0.0, FRONT_SIGN * dims["wall_base_radius"], 0.0)
    return _object_from_bmesh("Steps", bm, _materials(config, ["stone"]),
                              origin=origin, sharp_angle_deg=config["smooth_angle_deg"])


# ---------------------------------------------------------------------------
# Assembly and checks
# ---------------------------------------------------------------------------

def build_cottage(config: dict, dims: dict):
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    root = bpy.data.objects.new(ROOT_NAME, None)
    root.empty_display_size = 0.5
    collection.objects.link(root)

    parts = [
        build_walls(config, dims), build_base(config, dims), build_roof(config, dims),
        build_door(config, dims), build_door_frame(config, dims), build_window(config, dims),
        build_steps(config, dims),
    ]
    lantern, lantern_light = build_lantern(config, dims)
    parts.append(lantern)
    for obj in parts:
        collection.objects.link(obj)
        obj.parent = root
    collection.objects.link(lantern_light)
    return collection, root


def _mesh_objects(collection) -> list:
    return [obj for obj in collection.all_objects if obj.type == 'MESH']


def report_geometry(collection, config: dict, dims: dict) -> list:
    """Triangles per part, world bounds, node scale. Returns failure messages."""
    failures = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    min_z, max_z = math.inf, -math.inf
    for obj in sorted(_mesh_objects(collection), key=lambda o: o.name):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.data
        tris = sum(len(poly.vertices) - 2 for poly in mesh.polygons)
        total += tris
        for vert in mesh.vertices:
            z = (evaluated.matrix_world @ vert.co).z
            min_z, max_z = min(min_z, z), max(max_z, z)
        print(f"[{ASSET_NAME}] Part {obj.name:10s} {tris:5d} triangles")
    print(f"[{ASSET_NAME}] Triangles total {total} (budget {config['triangle_budget']})")
    print(f"[{ASSET_NAME}] Built height {max_z - min_z:.3f} (lowest point {min_z:.4f}, derived apex {dims['apex_z']:.3f})")
    if total > config["triangle_budget"]:
        failures.append(f"triangle budget exceeded: {total} > {config['triangle_budget']}")
    if abs(min_z) > 0.001:
        failures.append(f"ground contact: lowest point {min_z:.4f} != 0")
    for obj in collection.all_objects:
        if any(abs(s - 1.0) > 1e-6 for s in obj.scale):
            failures.append(f"node scale on {obj.name}: {tuple(obj.scale)}")
    return failures


def report_part_intersections(collection) -> list:
    from mathutils.bvhtree import BVHTree

    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = {}
    for obj in _mesh_objects(collection):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        verts = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        trees[obj.name] = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in mesh.polygons])
        evaluated.to_mesh_clear()

    failures = []
    for a, b in SEPARATE_PARTS:
        if a in trees and b in trees:
            pairs = trees[a].overlap(trees[b])
            if pairs:
                print(f"[{ASSET_NAME}] WARNING intersection: {a} x {b} ({len(pairs)} face pairs)")
                failures.append(f"intersection {a} x {b}")
    print(f"[{ASSET_NAME}] Part intersection check: {len(failures)} of {len(SEPARATE_PARTS)} pairs intersect")
    return failures


def export_glb(filepath: Path, collection) -> None:
    """Export only the cottage (runs before any preview object exists)."""
    members = set(collection.all_objects)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in members)
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='EXPORT',
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def report_glb(path: Path, collection) -> list:
    info = inspect_glb(path)
    failures = []
    print(f"[{ASSET_NAME}] GLB nodes: {', '.join(info['node_names'])}")
    print(f"[{ASSET_NAME}] GLB triangles {info['triangles']}, materials {info['materials']}, "
          f"cameras {info['cameras']}, lights {info['lights']}, scaled nodes {info['scaled_nodes'] or 'none'}")
    door = info["nodes"].get("Door", {})
    translation = door.get("translation", (0.0, 0.0, 0.0))
    print(f"[{ASSET_NAME}] GLB Door translation (glTF, +Z = front): {tuple(round(c, 3) for c in translation)}")
    if translation[2] <= abs(translation[0]):
        failures.append("GLB: door does not face +Z")
    if info["scaled_nodes"]:
        failures.append(f"GLB: scaled nodes {info['scaled_nodes']}")
    if info["cameras"] or info["lights"]:
        failures.append("GLB contains cameras or lights")
    expected = {obj.name for obj in collection.all_objects}
    missing = expected - set(info["node_names"])
    if missing:
        failures.append(f"GLB: missing nodes {sorted(missing)}")
    return failures


# ---------------------------------------------------------------------------
# Preview / check renders
# ---------------------------------------------------------------------------

def build_preview_setup(config: dict, dims: dict):
    collection = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    size = 20.0
    ground_mesh = bpy.data.meshes.new("Preview_Ground")
    ground_mesh.from_pydata([(-size, -size, 0.0), (size, -size, 0.0), (size, size, 0.0), (-size, size, 0.0)],
                            [], [(0, 1, 2, 3)])
    ground_mesh.materials.append(_materials(config, ["preview_ground"])[0])
    ground = bpy.data.objects.new("Preview_Ground", ground_mesh)
    collection.objects.link(ground)

    camera = bpy.data.objects.new("Preview_Camera", bpy.data.cameras.new("Preview_Camera"))
    camera.data.type = 'ORTHO'
    camera.data.sensor_fit = 'VERTICAL'
    camera.data.clip_end = 100.0
    collection.objects.link(camera)
    bpy.context.scene.camera = camera

    sun = bpy.data.objects.new("Preview_Sun", bpy.data.lights.new("Preview_Sun", type='SUN'))
    sun.data.energy = config["sun_strength"]
    sun.data.angle = math.radians(config["sun_angle_deg"])
    sun.rotation_euler = Vector(config["sun_direction"]).to_track_quat('-Z', 'Y').to_euler()
    collection.objects.link(sun)

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("Preview_World")
        bpy.context.scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    background = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if background is not None:
        background.inputs["Color"].default_value = srgb_to_linear(config["world_color"])
        background.inputs["Strength"].default_value = config["world_strength"]
    return camera


def aim_camera(camera, config: dict, dims: dict, yaw_deg: float, pitch_deg: float, resolution) -> None:
    target = (0.0, FRONT_SIGN * 0.2, dims["total_height"] * 0.45)
    camera.location, camera.rotation_euler = orbit_camera(target, yaw_deg, pitch_deg, config["preview_distance"])
    camera.data.ortho_scale = fit_ortho_scale(dims, pitch_deg, resolution[0] / resolution[1], config["preview_margin"])


def configure_render(scene, config: dict, resolution, samples: int, output_path: Path) -> None:
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output_path)


def _render(scene, path: Path) -> Path:
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[{ASSET_NAME}] Rendered {path}")
    return path


def _pixel_height(scene, camera, objects) -> float:
    from bpy_extras.object_utils import world_to_camera_view

    depsgraph = bpy.context.evaluated_depsgraph_get()
    ys = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        for vert in evaluated.data.vertices:
            ys.append(world_to_camera_view(scene, camera, evaluated.matrix_world @ vert.co).y)
    return (max(ys) - min(ys)) * scene.render.resolution_y if ys else 0.0


def render_game_size(scene, camera, collection, config: dict, output_dir: Path) -> list:
    """Cottage next to the Garden Wight at the S1 game camera's pixel density."""
    glb = Path(config["compare_glb"]).resolve()
    if not glb.exists():
        print(f"[{ASSET_NAME}] NOT RUN game-size comparison: {glb} missing (run garden_wight.py first)")
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    cx, cy = config["compare_position"]
    for obj in imported:
        if obj.parent is None:
            obj.location = (obj.location.x + cx, obj.location.y + cy, obj.location.z)
    bpy.context.view_layer.update()

    pitch = config["preview_pitch_deg"]
    camera.location, camera.rotation_euler = orbit_camera(
        config["game_view_target"], 0.0, pitch, config["preview_distance"])
    width_m, height_m = config["game_view_size"]
    written = []
    for factor in config["game_view_scales"]:
        density = config["game_px_per_m"] * factor
        res = (round(width_m * density), round(height_m * density))
        scene.render.resolution_x, scene.render.resolution_y = res
        camera.data.ortho_scale = res[1] / density
        bpy.context.view_layer.update()
        cottage_px = _pixel_height(scene, camera, collection.all_objects)
        wight_px = _pixel_height(scene, camera, imported)
        print(f"[{ASSET_NAME}] Game size x{factor}: {res[0]}x{res[1]} px, "
              f"cottage {cottage_px:.0f} px tall, Garden Wight {wight_px:.0f} px tall")
        written.append(_render(scene, output_dir / f"{ASSET_NAME}_game{factor}x.png"))
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(
        prog="bldg_cottage.py",
        description="Generate the Spirit Village Wurzelheim cottage (Blender-side).",
    )
    parser.add_argument("--output-dir", default="build/buildings/bldg_cottage",
                        help="Directory for .blend/.glb/.png (relative to the launch directory).")
    parser.add_argument("--render", action="store_true", help="Also render the 50 degree preview PNG.")
    parser.add_argument("--views", action="store_true",
                        help="Check set (implies --render): back, side and game-size comparison renders.")
    return parser.parse_args(argv)


def main() -> None:
    if bpy is None:
        sys.exit(
            "bldg_cottage.py must be run from inside Blender, e.g.:\n"
            "  blender --background --factory-startup --python-exit-code 1 --python "
            "art/generators/bldg_cottage.py -- --output-dir <dir> --views"
        )

    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{ASSET_NAME}] Blender {bpy.app.version_string}, API target: {BLENDER_API_TARGET}")
    print(f"[{ASSET_NAME}] Output directory: {output_dir}")

    dims = derive_dimensions(CONFIG)
    clear_scene()
    collection, _root = build_cottage(CONFIG, dims)
    bpy.context.view_layer.update()

    failures = report_geometry(collection, CONFIG, dims)
    failures += report_part_intersections(collection)

    glb_path = output_dir / f"{ASSET_NAME}.glb"
    export_glb(glb_path, collection)
    print(f"[{ASSET_NAME}] Exported GLB (cottage only): {glb_path}")
    failures += report_glb(glb_path, collection)

    camera = build_preview_setup(CONFIG, dims)
    scene = bpy.context.scene
    preview_res = CONFIG["preview_resolution"]
    aim_camera(camera, CONFIG, dims, 0.0, CONFIG["preview_pitch_deg"], preview_res)
    preview_path = output_dir / f"{ASSET_NAME}_preview.png"
    configure_render(scene, CONFIG, preview_res, CONFIG["preview_samples"], preview_path)

    blend_path = output_dir / f"{ASSET_NAME}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[{ASSET_NAME}] Saved .blend (cottage + preview setup): {blend_path}")

    if args.render or args.views:
        _render(scene, preview_path)
    if args.views:
        scene.cycles.samples = CONFIG["views_samples"]
        for name, yaw, pitch in (
            ("back", 180.0, CONFIG["preview_pitch_deg"]),
            ("side", 90.0, CONFIG["views_side_pitch_deg"]),
        ):
            aim_camera(camera, CONFIG, dims, yaw, pitch, preview_res)
            _render(scene, output_dir / f"{ASSET_NAME}_{name}.png")
        render_game_size(scene, camera, collection, CONFIG, output_dir)

    if failures:
        for failure in failures:
            print(f"[{ASSET_NAME}] CHECK FAILED: {failure}")
        raise RuntimeError(f"{len(failures)} check(s) failed")
    print(f"[{ASSET_NAME}] All checks passed")


if __name__ == "__main__":
    main()
