"""Wurzelheim stone oven generator (Spirit Village).

Builds ``bldg_oven``: a round dry-stone oven with an arched fire opening
towards the front, glowing embers in the fire chamber and in the top throat,
a sloped stone cap with an iron grate, and a dark cast-iron cauldron of
orange soup with two ring handles (art/PIPELINE.md, section 4a; reference
``mockup.png``, top right).

Conventions
-----------
* **Z-up** in Blender, ground contact at ``z = 0``, 1 unit = 1 m, origin at
  the centre of the footprint.
* The fire opening **faces -Y** in Blender, which the glTF exporter maps to
  glTF **+Z** (asset front, Godot ``Vector3.MODEL_FRONT``). Every run checks
  this in the exported GLB.
* Azimuths are measured around the wall from the front (0) towards +X (the
  viewer's right when looking at the opening). Wall coordinates use ``u`` =
  arc length at a fixed reference radius, ``v`` = height.
* Every size in CONFIG is a full extent (diameter / width / height). The
  stone courses, the arched opening frame and the cauldron profile are
  derived from those extents; the helpers stay free of ``bpy``.
* The stone courses are individual, irregular blocks on a dark mortar
  backing; the two stones in front of the opening are left out and the
  opening frame (jambs + voussoirs) closes that gap exactly.
* Movable or animated parts are their own nodes: ``Cauldron`` (origin at the
  pot's bottom, so it can be lifted), ``Soup``, ``Embers``, the empty
  ``SteamAnchor`` above the soup and ``FireLight`` inside the opening (both
  anchors for Godot effects). ``FireOpening`` carries origin at the front of
  the opening.

Contact pairs that are intentional (not listed in SEPARATE_PARTS): the
``Cauldron`` rests on the ``Base`` grate, ``Soup`` sits inside the cauldron,
``Embers`` lie on the ``FireOpening`` floor, and ``FireOpening`` interlocks
with the stone courses at the arch and the sill.

Environment and scene assumption
--------------------------------
Same as ``bldg_cottage.py``: the modelling code needs Blender's Python
(verified with Blender 5.2.1 LTS), the pure geometry helpers
(``derive_dimensions``, ``voussoir_polygon``, ``inspect_glb``) import without
``bpy``. ``clear_scene()`` wipes the scene, so only run this in its own
``--background --factory-startup`` process.

Usage (arguments after ``--``)
------------------------------
    blender --background --factory-startup --python-exit-code 1 --python \\
        art/generators/bldg_oven.py -- \\
        --output-dir build/buildings/bldg_oven [--render | --views]

The run fails (exit 1 with ``--python-exit-code 1``) when an automatic check
fails: triangle budget, ground contact, node scale, part intersections, the
opening direction in the GLB. All files are written before that.

Stand 2026-09-17: S9, first version (DeepSeek V4.1 Flash); renders reviewed
against ``mockup.png``.
"""

from __future__ import annotations

import argparse
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
# Configuration - the single place to tune the oven.
# Metres; full extents; azimuths in degrees from the front towards +X.
# ---------------------------------------------------------------------------

CONFIG = {
    # Masonry drum: individual stones on a dark mortar backing, nearly
    # cylindrical with only a slight barrel and taper.
    "base_bottom_diameter": 0.84,   # outside diameter at ground level
    "base_top_diameter": 0.82,      # outside diameter under the cap
    "base_bulge": 0.012,            # extra radius at mid height -> slight barrel
    "base_height": 0.62,            # ground to the top of the stone courses
    "course_count": 4,              # horizontal stone courses
    "stones_per_course": 17,        # joints per ring; chosen so the two stones in
                                    # front of the opening fit exactly
    "stone_split_chance": 0.55,     # share of stones split into two smaller ones
    "stone_split_joint": 0.006,     # joint between the halves of a split stone
    "stone_joint": 0.008,           # visible gap between stones in a course
    "stone_exposed": 0.13,          # radial stone depth in front of the backing
    "stone_bulge": 0.016,           # stones stand this far proud of the backing
    "stone_depth_jitter": 0.016,    # per-stone radial depth variation
    "stone_width_variation": 0.14,  # share of the width a stone may vary by
    "stone_height_variation": 0.24,  # share of the course height a stone may lose
    "stone_edge_jitter": 0.008,     # corner displacement -> irregular stones
    "stone_azimuth_jitter_deg": 1.2,
    "stone_tilt_jitter_deg": 1.8,
    "mortar_radius_share": 0.72,    # backing shell radius as a share of the
                                    # course radius (dark joints behind the stones)
    "mortar_thickness": 0.032,
    # Cap: a narrow stone rim with a raised inner collar that hugs the
    # cauldron's foot, so no glowing gap stays open between rim and pot.
    "plate_outer_diameter": 0.82,   # 1 cm lip over the top course
    "collar_height": 0.055,         # collar rises this far above the top course
    "plate_height": 0.012,          # crown of the rim above the collar
    "plate_inner_diameter": 0.30,   # collar bore, snug around the cauldron foot
    "plate_segments": 17,           # radial joints of the inner ring (wall bond)
    "plate_outer_segments": 12,     # outer ring, staggered against the inner one
    "plate_mid_diameter": 0.58,     # boundary between the two rim rings
    "plate_joint": 0.004,           # visible joint between the rim's stones
    "plate_skirt": 0.055,           # rim reaches this far down into the top course
    "grate_bar_length": 0.30,       # bars span the bore and rest on the collar
    "grate_bar_thickness": 0.022,
    "grate_recess": 0.008,          # grate sits this far below the collar top
    "grate_bars": 3,
    # Fire opening towards the front (-Y in Blender -> +Z in glTF).
    "opening_width": 0.24,          # clear width between the jambs (full extent)
    "opening_arch_radius": 0.12,    # = opening_width / 2 -> round arch
    "opening_sill": 0.155,          # = bottom of the second course
    "jamb_width": 0.035,            # stone frame beside the opening
    "jamb_proud": 0.03,             # frame stands this far out of the wall
    "voussoir_count": 7,
    "chamber_depth": 0.11,          # dark interior behind the opening
    "chamber_floor_height": 0.025,  # glowing floor slab above the sill stones
    # Embers and flames in the fire chamber, kept in the front half so the
    # 50 degree game camera sees them through the arched opening.
    "ember_bed_size": (0.16, 0.045, 0.02),   # glowing bed on the chamber floor
    "ember_bed_y": 0.250,           # centre distance of the bed from the oven axis
    "ember_count": 7,
    "ember_pile_count": 4,          # coals piled on top of the first layer
    "ember_size": (0.05, 0.05, 0.04),
    "ember_radius": (0.20, 0.25),   # centre distance from the oven axis
    "ember_level": 0.175,           # z of the first coal layer
    "ember_pile_level": 0.215,      # z of the piled coals
    "ember_sink": 0.006,            # coals sink this far into their bed
    "ember_tint": 0.30,             # share of coals using the darker ember colour
    "flame_count": 3,
    "flame_height": 0.21,           # bed to tip, reaching the opening's crown
    "flame_radius": 0.033,
    "flame_spread": 0.062,          # lateral offset of the tongues from the centre
    "flame_lean": 0.030,            # sideways sweep of a tongue towards its tip
    "flame_y": 0.245,               # centre distance of the tongues from the axis
    # Cauldron: dark cast iron, round belly, two ring handles.
    "cauldron_foot_diameter": 0.27,
    "cauldron_belly_diameter": 0.50,
    "cauldron_rim_diameter": 0.45,
    "cauldron_height": 0.35,        # foot bottom to rim (full extent)
    "cauldron_segments": 32,
    "cauldron_lip": 0.018,          # visible wall thickness at the rim
    "ear_radius": 0.034,            # ring handle radius
    "ear_tube": 0.011,
    "ear_proud": 0.022,             # handle centre outside the rim radius
    "ear_drop": 0.022,              # handle centre below the rim
    "ear_sides": 12,
    "ear_section": 6,
    # Soup surface inside the cauldron.
    "soup_level": 0.055,             # below the rim
    "soup_lip": 0.020,              # soup edge stops this far short of the wall
    "soup_thickness": 0.008,
    # Mesh budget and shading.
    "triangle_budget": 4000,        # art/PIPELINE.md section 7
    "smooth_angle_deg": 45.0,
    # Preview and check renders (never exported).
    "preview_pitch_deg": 50.0,
    "preview_distance": 14.0,       # orthographic: clipping only
    "preview_margin": 1.06,
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
    "game_view_size": (2.6, 2.8),         # visible area in metres (camera plane)
    "game_view_target": (0.1, -0.05, 0.5),
    "game_view_scales": (1, 3),           # 1 = logical px, 3 = typical 1080 px wide phone
    "compare_glb": "build/characters/garden_wight/garden_wight.glb",
    "compare_position": (0.60, -0.26),
    # Colours (matte, texture-free) as sRGB, like a colour picker or Godot's
    # albedo_color; converted to linear for Blender and the GLB.
    "colors": {
        "stone": (0.63, 0.58, 0.50, 1.0),
        "stone_alt": (0.57, 0.52, 0.45, 1.0),
        "stone_dark": (0.50, 0.45, 0.39, 1.0),
        "mortar": (0.28, 0.25, 0.22, 1.0),
        "soot": (0.19, 0.15, 0.13, 1.0),
        "chamber_glow": (0.70, 0.24, 0.06, 1.0),
        "iron": (0.21, 0.20, 0.20, 1.0),
        "ember": (1.0, 0.55, 0.18, 1.0),
        "ember_dark": (0.88, 0.34, 0.10, 1.0),
        "flame": (1.0, 0.74, 0.30, 1.0),
        "soup": (0.90, 0.42, 0.09, 1.0),
        "preview_ground": (0.42, 0.30, 0.20, 1.0),  # ground in game/scenes/garden.tscn
    },
    "emission": {                   # emission strength per colour key (0 = matte)
        "ember": 6.0,
        "ember_dark": 3.4,
        "chamber_glow": 1.1,
        "flame": 8.0,
        "soup": 0.35,
    },
}

ASSET_NAME = "bldg_oven"
COLLECTION_NAME = "Oven_Building"
PREVIEW_COLLECTION_NAME = "Oven_PreviewSetup"
ROOT_NAME = "Oven_Root"
BLENDER_API_TARGET = "5.2.1 LTS (verified); older versions untested"

# The opening faces -Y; preview cameras orbit from that side.
FRONT_SIGN = -1.0

# Parts that must not interpenetrate. Everything may sink into the masonry,
# the cauldron rests on the grate, the soup sits inside the pot, the embers lie
# on the fire-chamber floor and the frame interlocks with the stone courses.
SEPARATE_PARTS = (
    ("Cauldron", "FireOpening"),
    ("Cauldron", "Embers"),
    ("Cauldron", "Soup"),
    ("Soup", "Base"),
    ("Soup", "FireOpening"),
    ("Soup", "Embers"),
    ("Embers", "Base"),
)

MATERIAL_NAMES = {
    "stone": "Mat_Stone", "stone_alt": "Mat_StoneAlt", "stone_dark": "Mat_StoneDark",
    "mortar": "Mat_Mortar", "soot": "Mat_Soot", "chamber_glow": "Mat_ChamberGlow",
    "iron": "Mat_Iron", "ember": "Mat_EmberGlow", "ember_dark": "Mat_EmberGlowDark",
    "flame": "Mat_Flame", "soup": "Mat_Soup", "preview_ground": "Mat_PreviewGround",
}

# Base material slots: three stone shades, then mortar, then iron.
BASE_SLOTS = ("stone", "stone_alt", "stone_dark", "mortar", "iron")


# ---------------------------------------------------------------------------
# Pure geometry - no bpy, so these can be checked outside Blender.
# ---------------------------------------------------------------------------

def srgb_to_linear(rgba) -> tuple:
    """sRGB colour (0..1) -> linear, alpha unchanged."""
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(channel(c) for c in rgba[:3]) + tuple(rgba[3:])


def _hash01(*keys: float) -> float:
    """Deterministic pseudo-random value in [0, 1) - stable across runs."""
    x = math.sin(sum((i + 1) * 12.9898 * k + 78.233 * (i + 1) for i, k in enumerate(keys))) * 43758.5453
    return x - math.floor(x)


def shell_radius(z: float, config: dict) -> float:
    """Nominal outside radius of the stone drum at height ``z``."""
    t = min(max(z / config["base_height"], 0.0), 1.0)
    base = (config["base_bottom_diameter"]
            + (config["base_top_diameter"] - config["base_bottom_diameter"]) * t) / 2.0
    return base + config["base_bulge"] * math.sin(math.pi * t)


def wall_point(u: float, v: float, depth: float, config: dict, ref_radius: float) -> tuple:
    """Wall coordinates -> world point (front at -Y).

    ``u`` is arc length at ``ref_radius`` (positive towards +X seen from the
    front), ``v`` the height, ``depth`` the distance in front of the wall.
    """
    theta = u / ref_radius
    r = shell_radius(v, config) + depth
    return (r * math.sin(theta), FRONT_SIGN * r * math.cos(theta), v)


def derive_dimensions(config: dict) -> dict:
    """Resolve CONFIG into concrete placements (all world space, metres)."""
    d: dict = {}
    d["course_height"] = config["base_height"] / config["course_count"]
    d["opening_half"] = config["opening_width"] / 2.0
    d["frame_outer_half"] = d["opening_half"] + config["jamb_width"]
    d["spring"] = config["opening_sill"] + d["course_height"]
    d["crown"] = d["spring"] + config["opening_arch_radius"]
    d["arch_top"] = d["spring"] + d["course_height"]      # top of the second course
    d["opening_mid_z"] = (config["opening_sill"] + d["crown"]) / 2.0

    # One reference radius for the whole front frame, so the opening's edges
    # land on stone joints in every course.
    d["ref_radius"] = shell_radius(d["opening_mid_z"], config)
    d["az_step"] = 2.0 * math.pi / config["stones_per_course"]
    # Snap the frame's half angle onto the stone lattice: the opening then
    # spans exactly two stones and both frame edges hit a joint.
    raw = d["frame_outer_half"] / d["ref_radius"]
    spans = max(2.0, round(2.0 * raw / d["az_step"]))
    d["az_open"] = spans * d["az_step"] / 2.0
    d["frame_outer_half"] = d["az_open"] * d["ref_radius"]

    d["mortar_radius"] = shell_radius(config["base_height"] / 2.0, config) * config["mortar_radius_share"]
    d["mortar_radius"] = max(d["mortar_radius"], d["ref_radius"] - config["stone_exposed"] + 0.005)

    d["plate_top"] = config["base_height"] + config["collar_height"] + config["plate_height"]
    d["collar_top"] = config["base_height"] + config["collar_height"]
    d["collar_inner"] = config["plate_inner_diameter"] / 2.0
    d["grate_top"] = d["collar_top"] - config["grate_recess"]
    d["chamber_floor_z"] = config["opening_sill"] - config["chamber_floor_height"]

    d["cauldron_bottom"] = d["grate_top"]
    d["cauldron_top"] = d["cauldron_bottom"] + config["cauldron_height"]
    d["soup_z"] = d["cauldron_top"] - config["soup_level"]
    d["soup_radius"] = (config["cauldron_rim_diameter"] / 2.0 - config["cauldron_lip"]
                        - config["soup_lip"])

    d["total_height"] = d["cauldron_top"]
    d["footprint_radius"] = max(
        config["plate_outer_diameter"] / 2.0,
        shell_radius(config["base_height"] / 2.0, config),
    )
    return d


def stone_layout(config: dict, dims: dict) -> list:
    """Stones as dicts with centre, extents, azimuth and tilt - pure geometry.

    Stones sit on their course's bottom line and vary in width, height and
    depth, so the wall reads as irregular field stone. Courses 1 and 2 (the
    opening) skip the two stones in front of the arch; their lattice is
    phase-shifted onto ``+/- az_open`` so the frame closes the gap exactly.
    """
    stones = []
    n = config["stones_per_course"]
    step = dims["az_step"]
    ch = dims["course_height"]
    for course in range(config["course_count"]):
        z0 = course * ch
        z_mid = z0 + ch / 2.0
        r = shell_radius(z_mid, config)
        phase = -dims["az_open"] if course in (1, 2) else step * (0.5 if course % 2 else 0.0)
        for k in range(n):
            az_base = phase + (k + 0.5) * step
            if course in (1, 2):
                if az_base - step / 2.0 < dims["az_open"] and az_base + step / 2.0 > -dims["az_open"]:
                    continue
            az = az_base + math.radians(config["stone_azimuth_jitter_deg"]) * (_hash01(course, k, 1.0) - 0.5)
            full_width = 2.0 * r * math.sin(step / 2.0)
            width = (full_width - config["stone_joint"]) * (
                1.0 - config["stone_width_variation"] * _hash01(course, k, 2.0))
            depth = config["stone_exposed"] + config["stone_depth_jitter"] * (_hash01(course, k, 4.0) - 0.4)
            # Roughly half the stones split into two flatter ones stacked on top
            # of each other - more, smaller masonry without touching the joint
            # lattice that keeps the opening's edges aligned.
            split = _hash01(course, k, 7.0) < config["stone_split_chance"]
            rows = [1.0] if not split else [0.52, 0.44]
            z_cursor = z0
            for half, share in enumerate(rows):
                height = ch * share * (1.0 - config["stone_height_variation"]
                                       * _hash01(course, k, 3.0 + half)) - config["stone_joint"]
                radius = r - depth / 2.0 + config["stone_bulge"] * (_hash01(course, k, 5.0 + half) - 0.35)
                # The ground course keeps a flat bottom, so it must not tilt.
                tilt = 0.0 if course == 0 else math.radians(config["stone_tilt_jitter_deg"]) * (
                    _hash01(course, k, 6.0 + half) - 0.5)
                stones.append({
                    "course": course,
                    "azimuth": az + math.radians(0.8) * (_hash01(course, k, 9.0 + half) - 0.5),
                    "center": (radius * math.sin(az), FRONT_SIGN * radius * math.cos(az),
                               z_cursor + height / 2.0),
                    "extents": (depth, width * (1.0 - 0.10 * half), height),
                    "tilt": tilt,
                    "seed": course * 1000.0 + k * 7.0 + half,
                })
                z_cursor += height + config["stone_joint"]
    return stones


def cap_profiles(config: dict, dims: dict) -> tuple:
    """Closed ``(radius, z)`` cross-sections of the rim's inner and outer rings.

    The inner ring carries the collar around the cauldron's foot and the sloping
    shoulder; the outer ring closes the top and drops down over the stone course.
    Both reach below the course so the rim plugs into the wall.
    """
    r_in = config["plate_inner_diameter"] / 2.0
    r_mid = config["plate_mid_diameter"] / 2.0
    r_out = config["plate_outer_diameter"] / 2.0
    z_bot = config["base_height"] - config["plate_skirt"]
    z_collar = dims["collar_top"]
    z_top = dims["plate_top"]
    inner = [
        (r_in, z_bot),
        (r_in, z_collar),
        (r_mid, z_top),
        (r_mid, z_bot),
    ]
    outer = [
        (r_mid, z_bot),
        (r_mid, z_top),
        (r_out - 0.028, z_top - 0.008),
        (r_out, z_top - 0.026),
        (r_out, z_bot + 0.010),
        (r_out - 0.020, z_bot),
    ]
    return inner, outer


def voussoir_polygon(config: dict, dims: dict, phi0: float, phi1: float) -> list:
    """Outline of one arch stone in wall coordinates ``(u, v)``.

    The inner edge follows the round arch around ``(0, spring)``; the outer
    edge is clipped by the frame's outer band and by the top of the arch
    course, so a whole course face stays flat above the arch.
    """
    r = config["opening_arch_radius"]
    u_max = dims["frame_outer_half"]
    z_top = dims["arch_top"]
    spring = dims["spring"]

    def inner(phi):
        return (r * math.cos(phi), spring + r * math.sin(phi))

    def outer(phi):
        t = float("inf")
        c, s = math.cos(phi), math.sin(phi)
        if abs(c) > 1e-9:
            t = min(t, u_max / abs(c))
        if s > 1e-9:
            t = min(t, (z_top - spring) / s)
        return (t * c, spring + t * s)

    return [inner(phi0), inner(phi1), outer(phi1), outer(phi0)]


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
    """Vertical ortho extent that shows the whole oven (square footprint bound)."""
    pitch = math.radians(pitch_deg)
    span = 2.0 * dims["footprint_radius"]
    vertical = dims["total_height"] * math.cos(pitch) + span * math.sin(pitch)
    return max(vertical, span / aspect) * margin


# ---------------------------------------------------------------------------
# Small Blender helpers
# ---------------------------------------------------------------------------

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
    return [
        get_or_create_material(MATERIAL_NAMES[key], colors[key],
                               emission=config["emission"].get(key, 0.0))
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
        for j, face in enumerate(faces):
            face.material_index = material[j] if isinstance(material, list) else material


def _add_stone(bm, center, extents, rotation, material_index, jitter=0.0, seed=0.0,
               keep_bottom=False) -> list:
    """Irregular stone block: a cube with jittered corners (bottom stays flat)."""
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=Vector(extents), verts=verts)
    if jitter > 0.0:
        for i, vert in enumerate(verts):
            vert.co.x += (_hash01(seed, i, 11.0) - 0.5) * jitter
            vert.co.y += (_hash01(seed, i, 12.0) - 0.5) * jitter
            if not (keep_bottom and vert.co.z < 0.0):
                vert.co.z += (_hash01(seed, i, 13.0) - 0.5) * jitter
    if rotation is not None:
        bmesh.ops.rotate(bm, cent=Vector((0.0, 0.0, 0.0)), matrix=rotation, verts=verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=verts)
    for face in {f for v in verts for f in v.link_faces}:
        face.material_index = material_index
    return verts


def _add_box(bm, center, extents, material_index, rotation=None, jitter=0.0, seed=0.0) -> list:
    return _add_stone(bm, center, extents, rotation, material_index, jitter=jitter, seed=seed)


def _wall_prism(bm, to3d, polygon, d_back, d_front, material_index) -> None:
    """Closed prism on the wall: ``polygon`` in (u, v), extruded over the depth."""
    front = [bm.verts.new(to3d(u, v, d_front)) for u, v in polygon]
    back = [bm.verts.new(to3d(u, v, d_back)) for u, v in polygon]
    faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
    n = len(polygon)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((front[i], front[j], back[j], back[i])))
    for face in faces:
        face.material_index = material_index


def _lathe(bm, profile, segments, material_index, center=(0.0, 0.0)) -> None:
    """Surface of revolution around a vertical axis through ``center``.

    A profile point with radius 0 becomes a single vertex (pole), so closed
    profiles (cauldron, throat pit) come out manifold.
    """
    cx, cy = center
    rows = []
    for r, z in profile:
        if r <= 1e-9:
            rows.append([bm.verts.new((cx, cy, z))])
        else:
            rows.append([bm.verts.new((cx + r * math.sin(2.0 * math.pi * j / segments),
                                       cy + FRONT_SIGN * r * math.cos(2.0 * math.pi * j / segments), z))
                         for j in range(segments)])
    _bridge_rows(bm, rows, [material_index] * len(rows))


def _arc_block(bm, profile, a0: float, a1: float, material_index) -> None:
    """Closed stone block spanning a ``(radius, z)`` profile between two azimuths."""
    def point(a, r, z):
        return (r * math.sin(a), FRONT_SIGN * r * math.cos(a), z)

    left = [bm.verts.new(point(a0, r, z)) for r, z in profile]
    right = [bm.verts.new(point(a1, r, z)) for r, z in profile]
    faces = [bm.faces.new(list(reversed(left))), bm.faces.new(right)]
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((left[i], left[j], right[j], right[i])))
    for face in faces:
        face.material_index = material_index


def _flame(bm, center, base_z, height, radius, lean, material_index) -> None:
    """Tapered flame tongue with a slight sideways sweep, tip pointing up."""
    cx, cy = center
    profile = (
        (0.0, 0.00), (radius * 0.85, 0.00), (radius, 0.12), (radius * 0.72, 0.40),
        (radius * 0.42, 0.68), (radius * 0.16, 0.88), (0.0, 1.00),
    )
    segments = 10
    rows = []
    for r, t in profile:
        z = base_z + height * t
        dx = lean * t ** 1.4
        dy = lean * 0.35 * t ** 1.4
        if r <= 1e-9:
            rows.append([bm.verts.new((cx + dx, cy + dy, z))])
        else:
            rows.append([bm.verts.new((cx + dx + r * math.sin(2.0 * math.pi * j / segments),
                                       cy + dy + FRONT_SIGN * r * math.cos(2.0 * math.pi * j / segments), z))
                         for j in range(segments)])
    _bridge_rows(bm, rows, [material_index] * len(rows))


def _torus(bm, center, major, tube, around, section, material_index) -> None:
    """Ring handle in the XZ plane (its axis along Y), closed and manifold."""
    center = Vector(center)
    axis = Vector((0.0, 1.0, 0.0))
    rings = []
    for i in range(around):
        a = 2.0 * math.pi * i / around
        radial = Vector((math.cos(a), 0.0, math.sin(a)))
        point = center + radial * major
        rings.append([bm.verts.new(point + radial * (tube * math.cos(b)) + axis * (tube * math.sin(b)))
                      for b in (2.0 * math.pi * k / section for k in range(section))])
    faces = []
    for i in range(around):
        for k in range(section):
            m = (k + 1) % section
            faces.append(bm.faces.new((rings[i][k], rings[i][m], rings[(i + 1) % around][m],
                                       rings[(i + 1) % around][k])))
    for face in faces:
        face.material_index = material_index


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def build_base(config: dict, dims: dict):
    """Stone courses, dark mortar backing, sloping cap, iron grate bars."""
    bm = bmesh.new()
    mortar_slot = BASE_SLOTS.index("mortar")
    iron_slot = BASE_SLOTS.index("iron")

    # Dark backing shell behind the stone joints, open at the fire opening.
    radius = dims["mortar_radius"] + config["mortar_thickness"] / 2.0
    z = config["base_height"] / 2.0
    az = dims["az_open"]
    end = 2.0 * math.pi - dims["az_open"]
    seg = 26
    for i in range(seg):
        a0 = az + (end - az) * i / seg
        width = (end - az) / seg * radius * 2.0 * 1.14
        _add_box(bm, (radius * math.sin(a0), FRONT_SIGN * radius * math.cos(a0), z),
                 (config["mortar_thickness"], width, config["base_height"]), mortar_slot,
                 Matrix.Rotation(a0 - math.pi / 2.0, 3, 'Z'))

    # Stone courses.
    for stone in stone_layout(config, dims):
        rotation = (Matrix.Rotation(stone["azimuth"] - math.pi / 2.0, 3, 'Z')
                    @ Matrix.Rotation(stone["tilt"], 3, 'Y'))
        material = int(_hash01(stone["seed"], 20.0) * 3.0) % 3
        _add_stone(bm, stone["center"], stone["extents"], rotation, material,
                   jitter=config["stone_edge_jitter"], seed=stone["seed"],
                   keep_bottom=stone["course"] == 0)

    # Narrow stone rim: two staggered rings of blocks - inner ring with the
    # collar, outer ring closing the top - so it reads as a paved capping course.
    inner, outer = cap_profiles(config, dims)
    for profile, count, phase, seed in (
        (inner, config["plate_segments"], 0.0, 41.0),
        (outer, config["plate_outer_segments"], 0.5, 61.0),
    ):
        step = 2.0 * math.pi / count
        r_mid = sum(r for r, _z in profile) / len(profile)
        gap = config["plate_joint"] / max(r_mid, 0.1)
        for j in range(count):
            roll = _hash01(j, seed)
            shade = 0 if roll < 0.70 else (1 if roll < 0.90 else 2)
            _arc_block(bm, profile, step * (j + phase) + gap / 2.0,
                       step * (j + phase + 1) - gap / 2.0, shade)

    # Grate: iron bars recessed in the collar's bore, the cauldron resting on
    # them so the rim's collar hides the gap around the pot's foot.
    bar_z = dims["grate_top"] - config["grate_bar_thickness"] / 2.0
    for i in range(config["grate_bars"]):
        offset = (i - (config["grate_bars"] - 1) / 2.0) * 0.055
        _add_box(bm, (0.0, offset, bar_z),
                 (config["grate_bar_length"], config["grate_bar_thickness"],
                  config["grate_bar_thickness"]), iron_slot)

    return _object_from_bmesh("Base", bm, _materials(config, BASE_SLOTS), origin=(0.0, 0.0, 0.0),
                              sharp_angle_deg=config["smooth_angle_deg"])


def build_fire_opening(config: dict, dims: dict):
    """Arched stone frame, dark fire chamber and the dark throat pit.

    The frame's origin sits at the front of the opening, so the GLB check can
    read its translation.
    """
    soot_slot = 2
    glow_slot = 3
    bm = bmesh.new()
    ref = dims["ref_radius"]

    def to3d(u, v, depth):
        return wall_point(u, v, depth, config, ref)

    d_back = -config["stone_exposed"] + 0.012
    d_front = config["jamb_proud"]

    # Jambs: vertical frame stones from the sill up to the spring line.
    half = dims["opening_half"]
    outer = dims["frame_outer_half"]
    sill, spring = config["opening_sill"], dims["spring"]
    for sign in (-1.0, 1.0):
        polygon = [(sign * half, sill), (sign * outer, sill), (sign * outer, spring), (sign * half, spring)]
        if sign < 0.0:
            polygon.reverse()
        _wall_prism(bm, to3d, polygon, d_back, d_front, 0 if sign < 0.0 else 1)

    # Voussoirs: wedge stones between the arch and the top of the arch course.
    count = config["voussoir_count"]
    for i in range(count):
        phi0 = math.pi * i / count
        phi1 = math.pi * (i + 1) / count
        _wall_prism(bm, to3d, voussoir_polygon(config, dims, phi0, phi1), d_back, d_front, 1 if i % 2 else 0)

    # Fire chamber: glowing floor, dark back and side slabs plus a ceiling, so
    # the opening is never a black hole.
    ceiling_z = dims["arch_top"] + 0.055
    floor_z = dims["chamber_floor_z"] + config["chamber_floor_height"] / 2.0
    chamber_y = ref - config["stone_exposed"] - config["chamber_depth"] / 2.0
    width = 2.0 * outer
    _add_box(bm, (0.0, -chamber_y + config["chamber_depth"] / 2.0 - 0.02, floor_z),
             (width, config["chamber_depth"] + 0.06, config["chamber_floor_height"]), glow_slot)
    _add_box(bm, (0.0, -chamber_y, (floor_z + ceiling_z) / 2.0),
             (width, 0.02, ceiling_z - floor_z), soot_slot)
    for sign in (-1.0, 1.0):
        _add_box(bm, (sign * (outer - 0.01), -chamber_y + 0.02, (floor_z + ceiling_z) / 2.0),
                 (0.02, config["chamber_depth"] + 0.04, ceiling_z - floor_z), soot_slot)
    _add_box(bm, (0.0, -chamber_y + 0.02, ceiling_z),
             (width, config["chamber_depth"] + 0.04, 0.03), soot_slot)

    # Dark plug inside the collar's bore, keeping the view from above off the
    # drum's hollow interior.
    r_plug = dims["collar_inner"] - 0.015
    plug_top = dims["grate_top"] - 0.005
    _lathe(bm, [
        (0.0, plug_top - 0.10), (r_plug, plug_top - 0.10),
        (r_plug, plug_top), (0.0, plug_top),
    ], config["cauldron_segments"], soot_slot)

    origin = wall_point(0.0, dims["opening_mid_z"], config["jamb_proud"], config, ref)
    return _object_from_bmesh("FireOpening", bm,
                              _materials(config, ["stone", "stone_alt", "soot", "chamber_glow"]),
                              origin=origin, sharp_angle_deg=config["smooth_angle_deg"])


def build_embers(config: dict, dims: dict):
    """Glowing ember bed with coals and flame tongues in the fire chamber."""
    bm = bmesh.new()
    sx, sy, sz = config["ember_size"]
    bed_y = config["ember_bed_y"]

    # Glowing bed on the chamber floor, right behind the sill.
    bed_x, bed_dy, bed_h = config["ember_bed_size"]
    _add_box(bm, (0.0, -bed_y, config["opening_sill"] - bed_h / 2.0 + 0.004),
             (bed_x, bed_dy, bed_h), 0, jitter=0.004)

    low, high = config["ember_radius"]
    for i in range(config["ember_count"]):
        r = low + (high - low) * _hash01(i, 31.0)
        angle = math.radians(_hash01(i, 32.0) * 70.0) - math.radians(35.0)
        z = config["ember_level"] + sz * 0.3 * (_hash01(i, 38.0) - 0.5)
        size = (sx * (0.6 + 0.7 * _hash01(i, 33.0)), sy * (0.6 + 0.7 * _hash01(i, 34.0)),
                sz * (0.6 + 0.7 * _hash01(i, 35.0)))
        material = 1 if _hash01(i, 36.0) < config["ember_tint"] else 0
        _add_stone(bm, (r * math.sin(angle), -(r * math.cos(angle)), z - config["ember_sink"]), size,
                   Matrix.Rotation(math.radians(360.0 * _hash01(i, 37.0)), 3, 'Z'), material,
                   jitter=0.012, seed=900.0 + i)
    for i in range(config["ember_pile_count"]):
        r = low + (high - low) * _hash01(i, 45.0) * 0.85
        angle = math.radians(_hash01(i, 46.0) * 50.0) - math.radians(25.0)
        material = 1 if _hash01(i, 47.0) < config["ember_tint"] else 0
        _add_stone(bm, (r * math.sin(angle), -(r * math.cos(angle)), config["ember_pile_level"]),
                   (sx * 0.8, sy * 0.8, sz * 0.8),
                   Matrix.Rotation(math.radians(360.0 * _hash01(i, 48.0)), 3, 'Z'), material,
                   jitter=0.012, seed=950.0 + i)

    # Flame tongues rising in the front half of the chamber.
    flame_y = config["flame_y"]
    for i in range(config["flame_count"]):
        spread = (i - (config["flame_count"] - 1) / 2.0) * config["flame_spread"]
        lean = config["flame_lean"] * (1.0 if i % 2 else -0.6)
        height = config["flame_height"] * (0.75 + 0.45 * _hash01(i, 50.0))
        _flame(bm, (spread, -flame_y), config["opening_sill"] + 0.01, height,
               config["flame_radius"] * (0.85 + 0.3 * _hash01(i, 51.0)), lean, 2)

    origin = (0.0, -dims["ref_radius"] + config["stone_exposed"], config["opening_sill"])
    return _object_from_bmesh("Embers", bm,
                              _materials(config, ["ember", "ember_dark", "flame"]),
                              origin=origin, sharp_angle_deg=config["smooth_angle_deg"])


def _cauldron_profile(config: dict, dims: dict) -> list:
    """(radius, z) profile of the cauldron from the bottom centre over the rim."""
    z0 = dims["cauldron_bottom"]
    z1 = dims["cauldron_top"]
    h = z1 - z0
    foot = config["cauldron_foot_diameter"] / 2.0
    belly = config["cauldron_belly_diameter"] / 2.0
    rim = config["cauldron_rim_diameter"] / 2.0
    lip = config["cauldron_lip"]
    return [
        (0.0, z0),
        (foot * 0.85, z0),
        (foot, z0 + 0.06 * h),
        (foot * 1.30, z0 + 0.22 * h),
        (belly * 0.92, z0 + 0.40 * h),
        (belly, z0 + 0.60 * h),
        (belly * 0.98, z0 + 0.80 * h),
        (rim, z1),
        (rim - lip, z1 - 0.004),
        (rim - lip, dims["soup_z"] - 0.02),
        (dims["soup_radius"], dims["soup_z"] - 0.035),
        (0.0, dims["soup_z"] - 0.035),
    ]


def build_cauldron(config: dict, dims: dict):
    """Dark cast-iron cauldron with two ring handles; origin at its bottom centre."""
    bm = bmesh.new()
    _lathe(bm, _cauldron_profile(config, dims), config["cauldron_segments"], 0)
    rim_radius = config["cauldron_rim_diameter"] / 2.0
    for sign in (-1.0, 1.0):
        _torus(bm, (sign * (rim_radius + config["ear_proud"]), 0.0, dims["cauldron_top"] - config["ear_drop"]),
               config["ear_radius"], config["ear_tube"], config["ear_sides"], config["ear_section"], 0)
    origin = (0.0, 0.0, dims["cauldron_bottom"])
    return _object_from_bmesh("Cauldron", bm, _materials(config, ["iron"]), origin=origin,
                              sharp_angle_deg=config["smooth_angle_deg"])


def build_soup(config: dict, dims: dict):
    """Flat orange soup surface inside the cauldron; own node for animation."""
    bm = bmesh.new()
    top = dims["soup_z"]
    _lathe(bm, [
        (0.0, top - config["soup_thickness"]), (dims["soup_radius"], top - config["soup_thickness"]),
        (dims["soup_radius"], top), (0.0, top),
    ], config["cauldron_segments"], 0)
    return _object_from_bmesh("Soup", bm, _materials(config, ["soup"]), origin=(0.0, 0.0, top),
                              sharp_angle_deg=config["smooth_angle_deg"])


def build_anchors(config: dict, dims: dict) -> list:
    """Empty helper nodes: steam above the soup, fire light in the opening."""
    steam = bpy.data.objects.new("SteamAnchor", None)
    steam.empty_display_size = 0.06
    steam.location = (0.0, 0.0, dims["cauldron_top"] + 0.06)
    fire = bpy.data.objects.new("FireLight", None)
    fire.empty_display_size = 0.06
    fire.location = wall_point(0.0, (config["opening_sill"] + dims["crown"]) / 2.0,
                               -config["stone_exposed"] * 0.5, config, dims["ref_radius"])
    return [steam, fire]


# ---------------------------------------------------------------------------
# Assembly and checks
# ---------------------------------------------------------------------------

def build_oven(config: dict, dims: dict):
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    root = bpy.data.objects.new(ROOT_NAME, None)
    root.empty_display_size = 0.5
    collection.objects.link(root)

    parts = [
        build_base(config, dims), build_fire_opening(config, dims),
        build_embers(config, dims), build_cauldron(config, dims), build_soup(config, dims),
    ]
    for obj in parts:
        collection.objects.link(obj)
        obj.parent = root
    for anchor in build_anchors(config, dims):
        collection.objects.link(anchor)
        anchor.parent = root
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
        print(f"[{ASSET_NAME}] Part {obj.name:12s} {tris:5d} triangles")
    print(f"[{ASSET_NAME}] Triangles total {total} (budget {config['triangle_budget']})")
    print(f"[{ASSET_NAME}] Built height {max_z - min_z:.3f} (lowest point {min_z:.4f}, "
          f"derived top {dims['total_height']:.3f})")
    print(f"[{ASSET_NAME}] Oven body {dims['plate_top']:.3f} m tall, "
          f"cauldron rim {dims['cauldron_top']:.3f} m, opening crown {dims['crown']:.3f} m")
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
    """Export only the oven (runs before any preview object exists)."""
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
    opening = info["nodes"].get("FireOpening", {})
    translation = opening.get("translation", (0.0, 0.0, 0.0))
    print(f"[{ASSET_NAME}] GLB FireOpening translation (glTF, +Z = front): "
          f"{tuple(round(c, 3) for c in translation)}")
    if translation[2] <= abs(translation[0]):
        failures.append("GLB: fire opening does not face +Z")
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
    target = (0.0, FRONT_SIGN * 0.1, dims["total_height"] * 0.45)
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
    """Oven next to the Garden Wight at the S1 game camera's pixel density."""
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
        oven_px = _pixel_height(scene, camera, collection.all_objects)
        wight_px = _pixel_height(scene, camera, imported)
        print(f"[{ASSET_NAME}] Game size x{factor}: {res[0]}x{res[1]} px, "
              f"oven {oven_px:.0f} px tall, Garden Wight {wight_px:.0f} px tall")
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
        prog="bldg_oven.py",
        description="Generate the Spirit Village Wurzelheim stone oven (Blender-side).",
    )
    parser.add_argument("--output-dir", default="build/buildings/bldg_oven",
                        help="Directory for .blend/.glb/.png (relative to the launch directory).")
    parser.add_argument("--render", action="store_true", help="Also render the 50 degree preview PNG.")
    parser.add_argument("--views", action="store_true",
                        help="Check set (implies --render): back, side and game-size comparison renders.")
    return parser.parse_args(argv)


def main() -> None:
    if bpy is None:
        sys.exit(
            "bldg_oven.py must be run from inside Blender, e.g.:\n"
            "  blender --background --factory-startup --python-exit-code 1 --python "
            "art/generators/bldg_oven.py -- --output-dir <dir> --views"
        )

    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{ASSET_NAME}] Blender {bpy.app.version_string}, API target: {BLENDER_API_TARGET}")
    print(f"[{ASSET_NAME}] Output directory: {output_dir}")

    dims = derive_dimensions(CONFIG)
    clear_scene()
    collection, _root = build_oven(CONFIG, dims)
    bpy.context.view_layer.update()

    failures = report_geometry(collection, CONFIG, dims)
    failures += report_part_intersections(collection)

    glb_path = output_dir / f"{ASSET_NAME}.glb"
    export_glb(glb_path, collection)
    print(f"[{ASSET_NAME}] Exported GLB (oven only): {glb_path}")
    failures += report_glb(glb_path, collection)

    camera = build_preview_setup(CONFIG, dims)
    scene = bpy.context.scene
    preview_res = CONFIG["preview_resolution"]
    aim_camera(camera, CONFIG, dims, 0.0, CONFIG["preview_pitch_deg"], preview_res)
    preview_path = output_dir / f"{ASSET_NAME}_preview.png"
    configure_render(scene, CONFIG, preview_res, CONFIG["preview_samples"], preview_path)

    blend_path = output_dir / f"{ASSET_NAME}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[{ASSET_NAME}] Saved .blend (oven + preview setup): {blend_path}")

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
