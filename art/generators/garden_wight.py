"""Garden Wight character generator (Spirit Village).

Generates the first static version of the game's non-human player
character: a small, pear-shaped garden gnome ("Gartenwicht") with a
cream overcoat, an asymmetric moss-green leaf cap, dark round eyes, two
short rounded hand-stubs, two small dark-brown feet, and an ochre seed
bag on a shoulder strap.

Conventions
-----------
* **Z-up**, both foot soles on ``z = 0``, whole figure ~1 Blender unit tall.
* The character **faces -Y**: Blender's Front view (Numpad 1) looks from
  -Y towards +Y and therefore shows the face. The glTF exporter maps
  Blender -Y to glTF **+Z** (checked in the exported GLB: eye nodes sit at
  +Z), which is glTF's asset-front convention and Godot's
  ``Vector3.MODEL_FRONT`` - *not* Godot's -Z node forward (Godot import not
  yet run). Eyes, strap and preview camera all use this same front side
  (``FRONT_SIGN``). ``.L``/``.R`` follow Blender's mirror convention: the
  character's left side is +X.
* **Every size in CONFIG is a full extent** (diameter / length / width /
  height), never a radius. Parts are built with bmesh at unit size and
  scaled to those extents (baked into the mesh), so ``body_width`` really is the widest
  diameter of the finished body.

IMPORTANT - environment assumption
-----------------------------------
The modelling code only runs inside Blender's own Python (``bpy`` /
``bmesh`` only exist inside a running Blender process). Verified with
**Blender 5.2.1 LTS** (background, factory startup); older versions such
as 4.5 LTS are untested (see art/README.md).

The ``bpy`` import is deliberately soft: the pure geometry helpers
(``derive_dimensions`` and friends) can be imported and checked with a
plain Python interpreter, while ``main()`` still refuses to do anything
without Blender.

Scene assumption
-----------------
The script assumes it is launched as a **separate Blender background
process with a factory-startup scene**. ``clear_scene()`` wipes every
object, collection, mesh and material it finds, so this must never be
run against an artist's already-open working file.

Usage (inside Blender, arguments after ``--``)
-----------------------------------------------
    blender --background --factory-startup --python \\
        art/generators/garden_wight.py -- \\
        --output-dir build/characters/garden_wight [--render]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:  # Blender-only modules - see "environment assumption" above.
    import bpy
    import bmesh
    from mathutils import Vector
except ImportError:  # pragma: no cover - outside Blender
    bpy = None
    bmesh = None
    Vector = None


# ---------------------------------------------------------------------------
# Configuration - the single place to tune the character.
# All values are FULL extents in Blender units (diameter/length/width/height),
# ratios are fractions of ``body_height`` measured from the body's lowest point.
# ---------------------------------------------------------------------------

CONFIG = {
    # Overall proportions.
    "total_height_target": 1.0,   # reference value; the built height is reported, not forced
    "body_width": 0.62,           # widest diameter of the finished body
    "body_height": 0.70,          # lowest to highest point of the body blob
    "body_bottom_z": 0.045,       # body's lowest point above the ground, so the feet show
    # Feet - soles sit exactly on z = 0.
    "foot_length": 0.17,          # along Y
    "foot_width": 0.13,           # along X
    "foot_height": 0.09,          # along Z
    "foot_spacing": 0.17,         # centre-to-centre distance
    "foot_forward": 0.10,         # shift towards the face side; toes peek out under the belly
    # Hands (short rounded stubs, no fingers).
    "hand_length": 0.17,
    "hand_diameter": 0.12,
    "hand_height_ratio": 0.46,
    "hand_forward": 0.03,         # towards the face side, so the stubs don't read as ears from above
    "hand_embed": 0.35,           # fraction of hand_diameter pushed into the body
    "hand_angle_deg": 22.0,       # outward splay of the stubs' lower ends
    # Eyes.
    "eye_diameter": 0.075,
    "eye_spacing": 0.16,          # centre-to-centre distance
    "eye_height_ratio": 0.68,     # kept clear below the cap's brim
    "eye_protrusion": 0.35,       # fraction of eye_diameter standing out of the body
    "eye_shine_diameter": 0.024,  # small white catch-light; 0 disables it
    # Cap (asymmetric, folded tip). Rotates about its own base.
    "cap_base_diameter": 0.46,
    "cap_height": 0.30,
    "cap_base_height_ratio": 0.84,
    "cap_lean_deg": 10.0,         # sideways lean (about Y) -> asymmetry, tip towards +X
    "cap_bend_deg": 95.0,         # total droop of the upper tip, towards the lean side
    "cap_bend_start": 0.45,       # fraction of cap_height where the droop begins
    "cap_brim_width": 0.03,       # brim reaches this far past cap_base_diameter / 2
    "cap_brim_droop": 0.06,       # brim edge hangs this far below the cap base at the back/sides
    "cap_brim_front_lift": 0.8,   # fraction of the droop removed at the front (keeps the eyes clear)
    "cap_brim_thickness": 0.02,
    # Seed bag + strap.
    "bag_size": (0.15, 0.10, 0.17),   # full x, y, z extents
    "bag_height_ratio": 0.20,
    "bag_embed": 0.35,            # fraction of bag x-extent overlapping the flank
    "bag_flap_depth_ratio": 0.45, # how far the flap hangs down the bag front (fraction of bag height)
    "bag_flap_thickness": 0.016,
    # The strap is a loop on the bag side: up the front flank beside the face,
    # over the shoulder, down the back, both ends buried in the bag's top.
    # Angles are measured around the body from the front (0) towards the bag
    # side (90); the back half mirrors them (180 - angle).
    "strap_width": 0.05,          # across the band
    "strap_end_width": 0.024,     # tapered ends, so both fit inside the bag's depth
    "strap_taper_length": 0.05,   # height above the bag top over which the band narrows
    "strap_thickness": 0.018,     # band thickness
    "strap_lift": 0.006,          # gap between body surface and the band's inner side
    "strap_mid_ratio": 0.62,      # lower waypoint height (fraction of body_height)
    "strap_mid_angle_deg": 44.0,  # keeps the front run clear of the eyes and the hand
    "strap_upper_ratio": 0.72,
    "strap_upper_angle_deg": 64.0,
    "strap_shoulder_ratio": 0.82,  # crest over the shoulder, at 90 deg (the bag side)
    "strap_bag_inset": 0.25,      # anchor inset from the bag's front/back face, fraction of bag depth
    "strap_bury": 0.03,           # how far each end reaches down into the bag
    # Mesh detail (the GLB is a mobile asset; ~8k triangles in total).
    "body_segments": (48, 28),    # around, top-to-bottom
    "part_segments": (24, 12),    # feet, hands, eyes
    "cap_segments": (40, 20),     # around, along the spine
    "strap_samples_per_span": 16,
    "bag_bevel": 0.015,           # rounded bag edges, baked into the mesh
    "smooth_angle_deg": 50.0,     # edges sharper than this stay crisp (bag, strap, cap brim)
    # Preview only (never exported to GLB).
    "preview_pitch_deg": 50.0,    # camera tilt below the horizon
    "preview_distance": 3.0,      # orthographic: affects clipping/placement, not scale
    "preview_margin": 1.25,       # empty border around the figure
    "preview_resolution": (768, 1024),
    "views_samples": 32,          # Cycles samples for the --views check renders
    "views_side_pitch_deg": 20.0,
    "views_figure_heights": (96, 48),  # crops where the FIGURE (not the image) has this height
    # Colors (matte, texture-free).
    "colors": {
        "skin_cream": (0.93, 0.87, 0.74, 1.0),
        "cap_moss": (0.29, 0.42, 0.24, 1.0),
        "feet_brown": (0.24, 0.16, 0.10, 1.0),
        "eyes_dark": (0.05, 0.05, 0.06, 1.0),
        "eye_shine": (0.95, 0.95, 0.92, 1.0),
        "bag_ochre": (0.72, 0.51, 0.20, 1.0),
        "strap_ochre_dark": (0.55, 0.38, 0.15, 1.0),
        "preview_ground": (0.55, 0.50, 0.42, 1.0),
    },
}

COLLECTION_NAME = "GardenWight_Character"

# Parts that must never interpenetrate (checked on every run). Everything
# may touch the body, the eye shines sit in the eyes and the strap ends
# are buried in bag and flap on purpose.
SEPARATE_PARTS = (
    ("Hand.L", "Bag"), ("Hand.R", "Bag"), ("Hand.L", "BagFlap"), ("Hand.R", "BagFlap"),
    ("Hand.L", "Strap"), ("Hand.R", "Strap"),
    ("Strap", "Eye.L"), ("Strap", "Eye.R"), ("Strap", "Cap"),
    ("Cap", "Eye.L"), ("Cap", "Eye.R"), ("Cap", "Hand.L"), ("Cap", "Hand.R"),
    ("Foot.L", "Bag"), ("Foot.R", "Bag"),
)
PREVIEW_COLLECTION_NAME = "GardenWight_PreviewSetup"
BLENDER_API_TARGET = "5.2.1 LTS (verified); older versions untested"

# The character faces -Y; the preview camera sits on that same side.
FRONT_SIGN = -1.0

# Radius of the source sphere the body is deformed from.
SPHERE_RADIUS = 0.5

# How much narrower (fraction) the head end of the pear is than the belly.
PEAR_HEAD_TAPER = 0.26


# ---------------------------------------------------------------------------
# Pure geometry - no bpy, so these can be checked outside Blender.
# ---------------------------------------------------------------------------

def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    x = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def _pear_radius_factor(t: float) -> float:
    """Extra taper applied on top of the source sphere at height fraction t.

    The lower half keeps the sphere's full, rounded belly; the upper half
    narrows smoothly into the head, so head and trunk read as one soft
    pear without a seam ("Kopf und Rumpf gehen optisch ineinander über").

    First Blender run: the earlier ``sin(t*pi)**0.7`` belly multiplied the
    sphere's own falloff twice and produced a diamond with a pointed base.
    """
    t = min(max(t, 0.0), 1.0)
    return 1.0 - PEAR_HEAD_TAPER * _smoothstep(0.30, 0.85, t)


def _body_profile(t: float) -> float:
    """Body's XY radius at height fraction t, in units of SPHERE_RADIUS.

    Combines the source sphere's own latitude falloff with the pear
    taper, i.e. this is the silhouette the deformed mesh actually has.
    """
    latitude = 1.0 - (2.0 * t - 1.0) ** 2
    if latitude <= 0.0:
        return 0.0
    return math.sqrt(latitude) * _pear_radius_factor(t)


# Peak of the silhouette, used to normalise body_width to a true diameter.
_MAX_BODY_PROFILE = max(_body_profile(i / 2000.0) for i in range(2001))


def body_xy_scale(config: dict) -> float:
    """Factor applied to the source sphere's XY so the widest point of the
    finished body is exactly ``body_width / 2`` from the axis."""
    return (config["body_width"] / 2.0) / (SPHERE_RADIUS * _MAX_BODY_PROFILE)


def body_radius_at(z: float, config: dict) -> float:
    """XY radius of the body surface at world height ``z`` (0 outside the body)."""
    t = (z - config["body_bottom_z"]) / config["body_height"]
    if t <= 0.0 or t >= 1.0:
        return 0.0
    return SPHERE_RADIUS * _body_profile(t) * body_xy_scale(config)


def _height_at(config: dict, ratio: float) -> float:
    return config["body_bottom_z"] + config["body_height"] * ratio


def derive_dimensions(config: dict) -> dict:
    """Resolve every placement from CONFIG into concrete world-space values.

    All part positions are derived from the *actual* body surface radius
    at their height, so changing ``body_width`` / ``body_height`` moves
    eyes, hands, bag and strap along with it instead of drifting apart.
    """
    dims: dict = {}

    body_bottom = config["body_bottom_z"]
    body_top = body_bottom + config["body_height"]
    dims["body_center_z"] = body_bottom + config["body_height"] / 2.0
    dims["body_bottom_z"] = body_bottom
    dims["body_top_z"] = body_top
    dims["body_max_radius"] = config["body_width"] / 2.0

    # Feet: both soles exactly on the ground plane.
    dims["foot_center_z"] = config["foot_height"] / 2.0
    dims["foot_x"] = config["foot_spacing"] / 2.0
    dims["foot_y"] = FRONT_SIGN * config["foot_forward"]

    # Hands: seated against the flank, partly embedded.
    hand_z = _height_at(config, config["hand_height_ratio"])
    hand_r = body_radius_at(hand_z, config)
    dims["hand_z"] = hand_z
    hand_ring = hand_r + config["hand_diameter"] * (0.5 - config["hand_embed"])
    dims["hand_y"] = FRONT_SIGN * config["hand_forward"]
    dims["hand_x"] = math.sqrt(max(hand_ring ** 2 - config["hand_forward"] ** 2, 0.0))
    dims["body_radius_at_hands"] = hand_r

    # Eyes: on the body's surface of revolution at their height, then
    # pushed out along the surface normal direction so they read as beads.
    eye_z = _height_at(config, config["eye_height_ratio"])
    eye_r = body_radius_at(eye_z, config)
    eye_x = config["eye_spacing"] / 2.0
    surface_ring = eye_r + config["eye_diameter"] * config["eye_protrusion"]
    if surface_ring <= eye_x:
        raise ValueError(
            "eye_spacing is wider than the body at eye height - reduce "
            "eye_spacing or raise body_width / lower eye_height_ratio"
        )
    dims["eye_z"] = eye_z
    dims["eye_x"] = eye_x
    dims["eye_y"] = FRONT_SIGN * math.sqrt(surface_ring ** 2 - eye_x ** 2)
    dims["eye_ring_radius"] = surface_ring
    dims["body_radius_at_eyes"] = eye_r

    # Cap: origin at its base so the lean rotates around the brim.
    cap_base_z = _height_at(config, config["cap_base_height_ratio"])
    dims["cap_base_z"] = cap_base_z
    dims["cap_tip_z"] = cap_base_z + config["cap_height"]
    dims["body_radius_at_cap"] = body_radius_at(cap_base_z, config)

    # Bag: hangs off the flank opposite the cap's lean.
    bag_sign = -1.0 if config["cap_lean_deg"] >= 0.0 else 1.0
    bag_x_size, bag_y_size, bag_z_size = config["bag_size"]
    bag_z = _height_at(config, config["bag_height_ratio"])
    bag_r = body_radius_at(bag_z, config)
    dims["bag_sign"] = bag_sign
    dims["bag_center"] = (
        bag_sign * (bag_r + bag_x_size * (0.5 - config["bag_embed"])),
        FRONT_SIGN * bag_y_size * 0.25,
        bag_z,
    )
    dims["bag_top_z"] = bag_z + bag_z_size / 2.0
    dims["body_radius_at_bag"] = bag_r

    # Strap anchors: front and back of the bag's top, inset from the faces
    # (see strap_path() for the loop between them).
    bag_x, bag_y, _bag_z = dims["bag_center"]
    inset = bag_y_size * config["strap_bag_inset"]
    front_y = bag_y + FRONT_SIGN * (bag_y_size / 2.0 - inset)
    back_y = bag_y - FRONT_SIGN * (bag_y_size / 2.0 - inset)
    anchor_x = bag_x - bag_sign * bag_x_size * 0.25   # towards the body
    dims["strap_anchor_front"] = (anchor_x, front_y, dims["bag_top_z"])
    dims["strap_anchor_back"] = (anchor_x, back_y, dims["bag_top_z"])

    # Overall silhouette of the assembled figure.
    dims["total_height"] = max(dims["cap_tip_z"], body_top)
    dims["figure_width"] = 2.0 * (dims["hand_x"] + config["hand_diameter"] / 2.0)
    dims["figure_depth"] = max(
        config["body_width"],
        config["foot_length"],
        config["cap_base_diameter"],
    )

    dims.update(_derive_preview(config, dims))
    return dims


def _body_slope_at(z: float, config: dict, h: float = 1e-3) -> float:
    """d(radius)/dz of the body surface at height ``z``."""
    return (body_radius_at(z + h, config) - body_radius_at(z - h, config)) / (2.0 * h)


def _catmull_rom(p0, p1, p2, p3, t: float) -> tuple:
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * (2.0 * b + (c - a) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
               + (3.0 * b - a - 3.0 * c + d) * t3)
        for a, b, c, d in zip(p0, p1, p2, p3)
    )


def strap_path(config: dict, dims: dict, samples_per_span: int = 10) -> list:
    """Inner centre line of the strap loop, with the outward surface normal.

    Waypoints are given as ``(angle, z, extra)``: ``angle`` around the body
    from the front towards the bag side, ``z`` the height, ``extra`` the
    distance outside the body surface (plus ``strap_lift``). The loop runs
    bag front -> front flank -> over the shoulder at 90 deg -> back flank
    -> bag back, and both ends continue ``strap_bury`` down into the bag.
    Interpolation happens in that space with ``extra`` clamped to >= 0, so
    no sample can lie inside the body.

    Returns ``(x, y, z, nx, ny, nz)`` tuples.
    """
    bag_sign = dims["bag_sign"]
    lift = config["strap_lift"]

    def to_keys(point):
        x, y, z = point
        angle = math.atan2(bag_sign * x, FRONT_SIGN * y)
        return (angle, z, math.hypot(x, y) - body_radius_at(z, config) - lift)

    def surface(ratio_key, angle_key):
        return (math.radians(config[angle_key]), _height_at(config, config[ratio_key]), 0.0)

    bury = config["strap_bury"]
    front = dims["strap_anchor_front"]
    back = dims["strap_anchor_back"]
    mid = surface("strap_mid_ratio", "strap_mid_angle_deg")
    upper = surface("strap_upper_ratio", "strap_upper_angle_deg")
    crest = (math.pi / 2.0, _height_at(config, config["strap_shoulder_ratio"]), 0.0)
    keys = [
        to_keys((front[0], front[1], front[2] - bury)),
        to_keys(front),
        mid,
        upper,
        crest,
        (math.pi - upper[0], upper[1], 0.0),
        (math.pi - mid[0], mid[1], 0.0),
        to_keys(back),
        to_keys((back[0], back[1], back[2] - bury)),
    ]
    padded = [keys[0]] + keys + [keys[-1]]

    points = []
    spans = len(keys) - 1
    for span in range(spans):
        p0, p1, p2, p3 = padded[span:span + 4]
        last = span == spans - 1
        for i in range(samples_per_span + (1 if last else 0)):
            angle, z, extra = _catmull_rom(p0, p1, p2, p3, i / samples_per_span)
            radius = body_radius_at(z, config) + lift + max(extra, 0.0)
            dir_x, dir_y = bag_sign * math.sin(angle), FRONT_SIGN * math.cos(angle)
            # Surface of revolution: normal ~ (radial direction, -dr/dz).
            slope = _body_slope_at(z, config)
            norm = math.sqrt(1.0 + slope * slope)
            points.append((
                dir_x * radius, dir_y * radius, z,
                dir_x / norm, dir_y / norm, -slope / norm,
            ))
    return points


def _derive_preview(config: dict, dims: dict) -> dict:
    """Orthographic preview camera aimed at the figure from its front side."""
    pitch = math.radians(config["preview_pitch_deg"])
    # Camera looks towards +Y and downwards; rotation_euler.x = 90deg - pitch.
    forward = (0.0, math.cos(pitch), -math.sin(pitch))
    target_z = dims["total_height"] / 2.0
    distance = config["preview_distance"]

    res_x, res_y = config["preview_resolution"]
    aspect = res_x / res_y  # portrait, so ortho_scale spans the vertical

    # A world-vertical edge projects onto the camera's up axis by cos(pitch),
    # a world-horizontal (depth) edge by sin(pitch).
    vertical_need = dims["total_height"] * math.cos(pitch) + dims["figure_depth"] * math.sin(pitch)
    horizontal_need = dims["figure_width"] / aspect
    ortho_scale = max(vertical_need, horizontal_need) * config["preview_margin"]

    return {
        "camera_forward": forward,
        "camera_target": (0.0, 0.0, target_z),
        "camera_location": (
            -forward[0] * distance,
            -forward[1] * distance,
            target_z - forward[2] * distance,
        ),
        "camera_rotation": (math.radians(90.0 - config["preview_pitch_deg"]), 0.0, 0.0),
        "camera_ortho_scale": ortho_scale,
    }


# ---------------------------------------------------------------------------
# Small Blender helpers
# ---------------------------------------------------------------------------

def _link_only(obj, collection) -> None:
    """Make ``collection`` the only collection ``obj`` is linked into."""
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)


def _shade_smooth(mesh, sharp_angle_deg=None) -> None:
    """Smooth-shade every face; optionally keep edges above an angle sharp."""
    mesh.shade_smooth()
    if sharp_angle_deg is not None:
        mesh.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))


def _object_from_bmesh(name: str, bm, mesh_name=None):
    """Write ``bm`` into a new mesh + object via bpy.data (no operators)."""
    mesh = bpy.data.meshes.new(mesh_name or name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return bpy.data.objects.new(name, mesh)


def get_or_create_material(name: str, rgba):
    """Flat, matte Principled BSDF material - no external textures."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):  # node materials are the default from 5.0 on
        mat.use_nodes = True
    mat.diffuse_color = rgba
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.85
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def clear_scene() -> None:
    """Wipe the factory-startup scene down to nothing.

    Destructive by design - see the module docstring's "Scene
    assumption" section.
    """
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)


def _add_sphere(name: str, extents, location, segments, rotation=(0.0, 0.0, 0.0)):
    """UV sphere with full ``extents`` (x, y, z) baked into the mesh.

    Built with bmesh instead of ``bpy.ops.mesh.primitive_uv_sphere_add``:
    no context/poll dependency, and the GLB nodes carry no non-uniform
    scale (cleaner normals and physics in Godot).
    """
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments[0], v_segments=segments[1], radius=SPHERE_RADIUS)
    bmesh.ops.scale(bm, vec=Vector(extents), verts=bm.verts)
    obj = _object_from_bmesh(name, bm)
    obj.location = location
    obj.rotation_euler = rotation
    _shade_smooth(obj.data)
    return obj


def _add_rounded_box(name: str, extents, location, bevel: float):
    """Box with full ``extents`` and bevelled edges, baked into the mesh."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(extents), verts=bm.verts)
    bmesh.ops.bevel(
        bm, geom=list(bm.verts) + list(bm.edges), offset=bevel,
        offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES',
    )
    obj = _object_from_bmesh(name, bm)
    obj.location = location
    return obj


# ---------------------------------------------------------------------------
# Body parts
# ---------------------------------------------------------------------------

def build_body(config: dict, dims: dict):
    """Pear-shaped body+head blob, doubling as the cream overcoat.

    Design note: the "cremefarbener kurzer Überwurf" is not a separate
    garment mesh in this first static version - the body mesh itself is
    the visible cream overcoat surface (see art/README.md).
    """
    bm = bmesh.new()
    around, rings = config["body_segments"]
    bmesh.ops.create_uvsphere(bm, u_segments=around, v_segments=rings, radius=SPHERE_RADIUS)

    xy_scale = body_xy_scale(config)
    height_scale = config["body_height"] / (2.0 * SPHERE_RADIUS)
    for vert in bm.verts:
        t = (vert.co.z + SPHERE_RADIUS) / (2.0 * SPHERE_RADIUS)
        radial = _pear_radius_factor(t) * xy_scale
        vert.co.x *= radial
        vert.co.y *= radial
        vert.co.z *= height_scale

    obj = _object_from_bmesh("Body", bm)
    _shade_smooth(obj.data)
    obj.location = (0.0, 0.0, dims["body_center_z"])
    obj.data.materials.append(get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"]))
    return obj


def build_feet(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_FeetBrown", config["colors"]["feet_brown"])
    feet = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        obj = _add_sphere(
            f"Foot.{side}",
            segments=config["part_segments"],
            extents=(config["foot_width"], config["foot_length"], config["foot_height"]),
            location=(sign * dims["foot_x"], dims["foot_y"], dims["foot_center_z"]),
        )
        obj.data.materials.append(material)
        feet.append(obj)
    return feet


def build_hands(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"])
    hands = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        obj = _add_sphere(
            f"Hand.{side}",
            segments=config["part_segments"],
            extents=(config["hand_diameter"], config["hand_diameter"], config["hand_length"]),
            location=(sign * dims["hand_x"], dims["hand_y"], dims["hand_z"]),
            # Relaxed, hanging pose: the lower ends splay outwards. (Tilting the
            # upper ends out read as ears from the elevated preview camera.)
            rotation=(0.0, -sign * math.radians(config["hand_angle_deg"]), 0.0),
        )
        obj.data.materials.append(material)
        hands.append(obj)
    return hands


def build_eyes(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_EyesDark", config["colors"]["eyes_dark"])
    diameter = config["eye_diameter"]
    eyes = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        obj = _add_sphere(
            f"Eye.{side}",
            segments=config["part_segments"],
            extents=(diameter, diameter, diameter),
            location=(sign * dims["eye_x"], dims["eye_y"], dims["eye_z"]),
        )
        obj.data.materials.append(material)
        eyes.append(obj)

    shine = config["eye_shine_diameter"]
    if shine > 0.0:
        shine_material = get_or_create_material("Mat_EyeShine", config["colors"]["eye_shine"])
        for side, sign in (("L", 1.0), ("R", -1.0)):
            centre = Vector((sign * dims["eye_x"], dims["eye_y"], dims["eye_z"]))
            outward = Vector((centre.x, centre.y, 0.0)).normalized()
            # Same light direction on both eyes: up and towards the figure's right (-X).
            direction = (outward + Vector((-0.45, 0.0, 0.9))).normalized()
            obj = _add_sphere(
                f"EyeShine.{side}",
                extents=(shine, shine, shine),
                location=centre + direction * (diameter / 2.0 - shine * 0.2),
                segments=(12, 6),
            )
            obj.data.materials.append(shine_material)
            eyes.append(obj)
    return eyes


def build_cap(config: dict, dims: dict):
    """Asymmetric moss-green leaf cap with a drooping tip.

    Built directly as a cone swept along a curved spine: straight up to
    ``cap_bend_start``, then curling by ``cap_bend_deg`` towards +X (the
    lean side). The mesh origin sits at the brim centre, so
    ``cap_lean_deg`` tilts the cap around its base.

    First Blender run: a Simple Deform (Bend, axis X) modifier used here
    before bent the cone across its width and left a flat, floating sail,
    hence the explicit geometry (no modifier to apply on export).
    """
    segments, rings = config["cap_segments"]
    height = config["cap_height"]
    base_radius = config["cap_base_diameter"] / 2.0
    bend = math.radians(config["cap_bend_deg"])
    bend_start = config["cap_bend_start"]

    bm = bmesh.new()
    # Spine lies in the XZ plane, so every ring uses the same fixed Y axis
    # and the cross-section cannot twist.
    position = Vector((0.0, 0.0, 0.0))
    step = height / rings
    ring_verts = []
    for i in range(rings + 1):
        s = i / rings
        curl = max(0.0, (s - bend_start) / (1.0 - bend_start)) ** 1.5
        angle = bend * curl
        tangent = Vector((math.sin(angle), 0.0, math.cos(angle)))
        side = Vector((0.0, 1.0, 0.0))
        normal = side.cross(tangent)  # in-plane, perpendicular to the spine
        if i > 0:
            position = position + tangent * step
        radius = base_radius * (1.0 - s) ** 0.85
        if i == rings:
            ring_verts.append([bm.verts.new(position)])
            break
        ring = []
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            ring.append(bm.verts.new(position + (normal * math.cos(phi) + side * math.sin(phi)) * radius))
        ring_verts.append(ring)

    for lower, upper in zip(ring_verts[:-1], ring_verts[1:-1]):
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((lower[j], lower[k], upper[k], upper[j]))
    last, tip = ring_verts[-2], ring_verts[-1][0]
    for j in range(segments):
        bm.faces.new((last[j], last[(j + 1) % segments], tip))
    # Brim: from the cone base, flare out and down to a rounded lip, then
    # back under towards the head. The droop is strongest at the back and
    # sides; at the front most of it is lifted so the eyes stay clear.
    width = config["cap_brim_width"]
    droop = config["cap_brim_droop"]
    thickness = config["cap_brim_thickness"]
    lift = config["cap_brim_front_lift"]
    brim_profile = (
        (base_radius + width, -1.0, 0.0),                           # outer lip
        (base_radius + width - thickness * 0.6, -1.0, thickness),   # under the lip
        (base_radius * 0.85, 0.0, thickness * 0.5),                 # underside, inside the head
    )
    base_ring = ring_verts[0]
    previous = base_ring
    for radius, droop_share, rise in brim_profile:
        ring = []
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            # side = +Y, so sin(phi) = -1 is the figure's front (-Y).
            front = max(0.0, -math.sin(phi)) ** 1.5
            drop = droop * (1.0 - lift * front) * -droop_share
            ring.append(bm.verts.new((math.cos(phi) * radius, math.sin(phi) * radius, -drop + rise)))
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((ring[j], ring[k], previous[k], previous[j]))
        previous = ring
    bm.faces.new(list(previous))  # closed underside
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    obj = _object_from_bmesh("Cap", bm)
    _shade_smooth(obj.data, config["smooth_angle_deg"])  # keeps the brim edge crisp
    obj.location = (0.0, 0.0, dims["cap_base_z"])
    obj.rotation_euler = (0.0, math.radians(config["cap_lean_deg"]), 0.0)
    obj.data.materials.append(get_or_create_material("Mat_CapMoss", config["colors"]["cap_moss"]))
    return obj


def build_strap(config: dict, dims: dict):
    """Closed band following the body surface along ``strap_path()``.

    Earlier versions: a straight box sank into the chest; a front-only band
    across the belly read as a mouth from the 50 degree preview camera.
    """
    thickness = config["strap_thickness"]
    taper_top = dims["bag_top_z"] + config["strap_taper_length"]
    path = strap_path(config, dims, config["strap_samples_per_span"])

    bm = bmesh.new()
    sections = []
    for i, (x, y, z, nx, ny, nz) in enumerate(path):
        prev_pt = Vector(path[max(i - 1, 0)][:3])
        next_pt = Vector(path[min(i + 1, len(path) - 1)][:3])
        along = (next_pt - prev_pt).normalized()
        outward = Vector((nx, ny, nz))
        across = along.cross(outward).normalized()
        taper = _smoothstep(dims["bag_top_z"], taper_top, z)
        half_width = 0.5 * (config["strap_end_width"]
                            + (config["strap_width"] - config["strap_end_width"]) * taper)
        inner = Vector((x, y, z))
        outer = inner + outward * thickness
        sections.append([
            bm.verts.new(inner - across * half_width),
            bm.verts.new(outer - across * half_width),
            bm.verts.new(outer + across * half_width),
            bm.verts.new(inner + across * half_width),
        ])
    for a, b in zip(sections[:-1], sections[1:]):
        for j in range(4):
            k = (j + 1) % 4
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bm.faces.new(sections[0])
    bm.faces.new(list(reversed(sections[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    obj = _object_from_bmesh("Strap", bm)
    _shade_smooth(obj.data, config["smooth_angle_deg"])  # smooth along, crisp band edges
    return obj


def build_bag_and_strap(config: dict, dims: dict) -> tuple:
    bag = _add_rounded_box("Bag", config["bag_size"], dims["bag_center"], config["bag_bevel"])
    _shade_smooth(bag.data, config["smooth_angle_deg"])
    bag.data.materials.append(get_or_create_material("Mat_BagOchre", config["colors"]["bag_ochre"]))

    # Flap: a lid on top that folds over the upper front of the bag. The
    # strap ends pass through it into the bag.
    bag_x, bag_y, bag_z = dims["bag_center"]
    size_x, size_y, size_z = config["bag_size"]
    flap_t = config["bag_flap_thickness"]
    flap_drop = size_z * config["bag_flap_depth_ratio"]
    overhang = flap_t * 0.6
    bm = bmesh.new()
    for extents, centre in (
        ((size_x + 2 * overhang, size_y + 2 * overhang, flap_t),
         (0.0, 0.0, size_z / 2.0 + flap_t / 2.0 - overhang * 0.5)),
        ((size_x + 2 * overhang, flap_t, flap_drop),
         (0.0, FRONT_SIGN * (size_y / 2.0 + flap_t / 2.0 - overhang * 0.5), size_z / 2.0 - flap_drop / 2.0)),
    ):
        part = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, vec=Vector(extents), verts=part)
        bmesh.ops.translate(bm, vec=Vector(centre), verts=part)
    bmesh.ops.bevel(
        bm, geom=list(bm.verts) + list(bm.edges), offset=flap_t * 0.35,
        offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES',
    )
    flap = _object_from_bmesh("BagFlap", bm)
    flap.location = (bag_x, bag_y, bag_z)
    _shade_smooth(flap.data, config["smooth_angle_deg"])
    flap.data.materials.append(
        get_or_create_material("Mat_StrapOchreDark", config["colors"]["strap_ochre_dark"])
    )

    strap = build_strap(config, dims)
    strap.data.materials.append(
        get_or_create_material("Mat_StrapOchreDark", config["colors"]["strap_ochre_dark"])
    )
    return bag, flap, strap


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_character(config: dict, dims: dict):
    char_coll = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(char_coll)

    root = bpy.data.objects.new("GardenWight_Root", None)
    root.empty_display_size = 0.1
    char_coll.objects.link(root)

    parts = [build_body(config, dims)]
    parts.extend(build_feet(config, dims))
    parts.extend(build_hands(config, dims))
    parts.extend(build_eyes(config, dims))
    parts.append(build_cap(config, dims))
    parts.extend(build_bag_and_strap(config, dims))

    for obj in parts:
        _link_only(obj, char_coll)
        obj.parent = root

    return char_coll, root


def report_bounding_height(collection, dims: dict, config: dict) -> None:
    """Print the assembled figure's real world-space height.

    Cheap feedback on the first actual Blender run: compares the built
    mesh against the derived prediction without failing the run, since
    the final proportions are meant to be tuned visually.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    min_z = math.inf
    max_z = -math.inf
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        eval_obj = obj.evaluated_get(depsgraph)
        for corner in eval_obj.bound_box:
            world_z = (eval_obj.matrix_world @ Vector(corner)).z
            min_z = min(min_z, world_z)
            max_z = max(max_z, world_z)
    if min_z is math.inf:
        return
    print(
        f"[garden_wight] Built height {max_z - min_z:.3f} "
        f"(lowest point {min_z:.3f}, derived {dims['total_height']:.3f}, "
        f"target ~{config['total_height_target']:.2f})"
    )


def report_part_intersections(collection) -> int:
    """Print every ``SEPARATE_PARTS`` pair whose meshes intersect; return the count."""
    from mathutils.bvhtree import BVHTree

    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = {}
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        verts = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        polys = [tuple(poly.vertices) for poly in mesh.polygons]
        trees[obj.name] = BVHTree.FromPolygons(verts, polys)
        evaluated.to_mesh_clear()

    hits = 0
    for a, b in SEPARATE_PARTS:
        if a in trees and b in trees:
            pairs = trees[a].overlap(trees[b])
            if pairs:
                hits += 1
                print(f"[garden_wight] WARNING intersection: {a} x {b} ({len(pairs)} face pairs)")
    print(f"[garden_wight] Part intersection check: {hits} of {len(SEPARATE_PARTS)} pairs intersect")
    return hits


# ---------------------------------------------------------------------------
# Export / preview / render
# ---------------------------------------------------------------------------

def export_glb(filepath: Path, collection) -> None:
    """Export only the character (geometry + materials) as GLB.

    Called before the preview setup exists, so no camera, light or
    ground plane can leak into the file. The glTF exporter converts to
    Y-up: the -Y face ends up on glTF +Z.
    """
    view_layer = bpy.context.view_layer
    members = set(collection.all_objects)
    for obj in view_layer.objects:
        obj.select_set(obj in members)

    # The exporter is an operator by nature; it needs no UI context in
    # background mode, so no temp_override is required here.
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format='GLB',
        use_selection=True,
        export_apply=True,       # no modifiers are used; kept as a safety net
        export_materials='EXPORT',
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def build_preview_setup(config: dict, dims: dict):
    """Ground plane, soft sun and an orthographic camera aimed at the figure.

    Local preview only - never part of the GLB (see export_glb()).
    """
    preview_coll = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
    bpy.context.scene.collection.children.link(preview_coll)

    ground_mesh = bpy.data.meshes.new("Preview_Ground")
    ground_mesh.from_pydata([(-2.0, -2.0, 0.0), (2.0, -2.0, 0.0), (2.0, 2.0, 0.0), (-2.0, 2.0, 0.0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("Preview_Ground", ground_mesh)
    ground.data.materials.append(
        get_or_create_material("Mat_PreviewGround", config["colors"]["preview_ground"])
    )
    _link_only(ground, preview_coll)

    camera = bpy.data.objects.new("Preview_Camera", bpy.data.cameras.new("Preview_Camera"))
    camera.location = dims["camera_location"]
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = dims["camera_ortho_scale"]
    camera.rotation_euler = dims["camera_rotation"]
    _link_only(camera, preview_coll)

    sun = bpy.data.objects.new("Preview_Sun", bpy.data.lights.new("Preview_Sun", type='SUN'))
    sun.location = (1.5, FRONT_SIGN * 1.5, dims["total_height"] + 1.5)
    sun.data.energy = 2.5
    sun.data.angle = math.radians(20.0)  # wide angle -> soft shadow edges
    _link_only(sun, preview_coll)

    bpy.context.scene.camera = camera
    return camera, ground


def configure_render(scene, config: dict, output_path: Path) -> None:
    """Apply the preview render settings.

    Always called *before* saving the .blend, so the saved preview and
    any PNG produced by --render use identical settings.

    Cycles on CPU: this pipeline assumes no guaranteed GPU wherever the
    render is produced (e.g. a headless box), and Cycles' CPU device is
    the most portable still-image path across Blender installs.
    """
    res_x, res_y = config["preview_resolution"]
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output_path)


def _figure_pixel_box(scene, camera, collection) -> tuple:
    """Pixel box (x0, y0, x1, y1; origin bottom-left) of the figure in ``camera``."""
    from bpy_extras.object_utils import world_to_camera_view

    res_x, res_y = scene.render.resolution_x, scene.render.resolution_y
    depsgraph = bpy.context.evaluated_depsgraph_get()
    xs, ys = [], []
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        for vert in evaluated.data.vertices:
            co = world_to_camera_view(scene, camera, evaluated.matrix_world @ vert.co)
            xs.append(co.x * res_x)
            ys.append(co.y * res_y)
    return min(xs), min(ys), max(xs), max(ys)


def write_figure_height_crops(scene, camera, collection, config: dict, preview_png: Path) -> list:
    """Crop the rendered preview to the figure and scale it so the *figure*
    is exactly each of ``views_figure_heights`` pixels tall."""
    import numpy as np

    x0, y0, x1, y1 = _figure_pixel_box(scene, camera, collection)
    figure_height = y1 - y0
    print(f"[garden_wight] Figure height in preview: {figure_height:.0f} px of {scene.render.resolution_y} px image height")

    source = bpy.data.images.load(str(preview_png))
    width, height = source.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    source.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    pad = 0.08 * figure_height
    crop = pixels[
        int(max(y0 - pad, 0)):int(min(y1 + pad, height)),
        int(max(x0 - pad, 0)):int(min(x1 + pad, width)),
    ]
    bpy.data.images.remove(source)

    written = []
    for target in config["views_figure_heights"]:
        scale = target / figure_height
        image = bpy.data.images.new(f"fig{target}", crop.shape[1], crop.shape[0], alpha=True)
        image.pixels.foreach_set(crop.ravel())
        image.scale(max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale)))
        path = preview_png.with_name(f"garden_wight_fig{target}px.png")
        image.filepath_raw = str(path)
        image.file_format = 'PNG'
        image.save()
        bpy.data.images.remove(image)
        written.append(path)
    return written


def render_check_views(scene, camera, dims: dict, config: dict, output_dir: Path) -> list:
    """Back view (same 50 degree pitch) and bag-side view for visual review.

    Orbits the preview camera around its aim point; the .blend is already
    saved at this point, so the stored preview setup stays unchanged.
    """
    scene.cycles.samples = config["views_samples"]
    aim = Vector(dims["camera_target"])
    distance = config["preview_distance"]
    side_yaw = 90.0 if dims["bag_sign"] > 0 else -90.0
    views = (
        ("back", 180.0, config["preview_pitch_deg"]),
        ("side_bag", side_yaw, config["views_side_pitch_deg"]),
    )
    written = []
    for name, yaw_deg, pitch_deg in views:
        yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
        # yaw 0 is the front camera on -Y (FRONT_SIGN); positive yaw orbits counter-clockwise.
        horizontal = Vector((math.sin(yaw), FRONT_SIGN * math.cos(yaw), 0.0))
        camera.location = aim + (horizontal * math.cos(pitch) + Vector((0.0, 0.0, math.sin(pitch)))) * distance
        camera.rotation_euler = (math.pi / 2.0 - pitch, 0.0, yaw)
        path = output_dir / f"garden_wight_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(
        prog="garden_wight.py",
        description="Generate the Spirit Village Garden Wight character (Blender-side).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="build/characters/garden_wight",
        help=(
            "Directory to write garden_wight.blend / .glb (and the preview "
            "PNG with --render) into. Relative paths are resolved against "
            "the working directory Blender was launched from. "
            "Default: build/characters/garden_wight"
        ),
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also render the PNG preview (orthographic, ~50 degree downward tilt).",
    )
    parser.add_argument(
        "--views",
        action="store_true",
        help=(
            "Visual check set (implies --render): back and bag-side renders plus "
            "preview crops at 96/48 px figure height."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    if bpy is None:
        sys.exit(
            "garden_wight.py must be run from inside Blender, e.g.:\n"
            "  blender --background --factory-startup --python "
            "art/generators/garden_wight.py -- --output-dir <dir>\n"
            "It cannot build the character with a plain Python interpreter."
        )

    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[garden_wight] Blender {bpy.app.version_string}, API target: {BLENDER_API_TARGET}")
    print(f"[garden_wight] Output directory: {output_dir}")

    dims = derive_dimensions(CONFIG)
    clear_scene()

    char_coll, _root = build_character(CONFIG, dims)
    report_bounding_height(char_coll, dims, CONFIG)
    report_part_intersections(char_coll)

    glb_path = output_dir / "garden_wight.glb"
    export_glb(glb_path, char_coll)
    print(f"[garden_wight] Exported GLB (figure only, no camera/light/ground): {glb_path}")

    camera, _ground = build_preview_setup(CONFIG, dims)

    png_path = output_dir / "garden_wight_preview.png"
    configure_render(bpy.context.scene, CONFIG, png_path)

    blend_path = output_dir / "garden_wight.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[garden_wight] Saved preview .blend (character + preview setup): {blend_path}")

    if args.render or args.views:
        bpy.ops.render.render(write_still=True)
        print(f"[garden_wight] Rendered preview PNG: {png_path}")

    if args.views:
        for path in write_figure_height_crops(bpy.context.scene, camera, char_coll, CONFIG, png_path):
            print(f"[garden_wight] Wrote figure-height crop: {path}")
        for path in render_check_views(bpy.context.scene, camera, dims, CONFIG, output_dir):
            print(f"[garden_wight] Rendered check view: {path}")


if __name__ == "__main__":
    main()
