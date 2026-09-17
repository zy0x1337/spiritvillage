"""Garden Wight character generator (Spirit Village).

Generates the first static version of the game's non-human player
character: a small, pear-shaped garden gnome ("Gartenwicht") with a
cream overcoat, an asymmetric moss-green leaf cap, dark round eyes, two
short rounded hand-stubs, two small dark-brown feet, and an ochre seed
bag on a diagonal strap.

Conventions
-----------
* **Z-up**, both foot soles on ``z = 0``, whole figure ~1 Blender unit tall.
* The character **faces -Y**: Blender's Front view (Numpad 1) looks from
  -Y towards +Y and therefore shows the face, and -Y maps to the -Z
  forward axis that Godot expects after the glTF Y-up conversion. Eyes,
  strap and preview camera all use this same front side (``FRONT_SIGN``).
* **Every size in CONFIG is a full extent** (diameter / length / width /
  height), never a radius. Primitives are created at unit size and
  scaled to those extents, so ``body_width`` really is the widest
  diameter of the finished body.

IMPORTANT - environment assumption
-----------------------------------
The modelling code only runs inside Blender's own Python (``bpy`` /
``bmesh`` only exist inside a running Blender process). It targets the
**Blender 4.5 LTS** Python/glTF API as a provisional baseline; the
version installed on the artist's machine has not been confirmed yet -
check ``bpy.app.version`` before relying on API details here (see
art/README.md).

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
    from mathutils import Matrix, Vector
except ImportError:  # pragma: no cover - outside Blender
    bpy = None
    bmesh = None
    Matrix = None
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
    "foot_forward": 0.025,        # shift towards the face side
    # Hands (short rounded stubs, no fingers).
    "hand_length": 0.17,
    "hand_diameter": 0.14,
    "hand_height_ratio": 0.52,
    "hand_embed": 0.35,           # fraction of hand_diameter pushed into the body
    "hand_angle_deg": 22.0,       # outward lean of the stubs
    # Eyes.
    "eye_diameter": 0.075,
    "eye_spacing": 0.16,          # centre-to-centre distance
    "eye_height_ratio": 0.74,     # kept clear below the cap's brim
    "eye_protrusion": 0.35,       # fraction of eye_diameter standing out of the body
    # Cap (asymmetric, folded tip). Rotates about its own base.
    "cap_base_diameter": 0.46,
    "cap_height": 0.30,
    "cap_base_height_ratio": 0.90,
    "cap_lean_deg": 16.0,         # sideways lean (about Y) -> asymmetry
    "cap_bend_deg": 55.0,         # folds the upper part of the tip over
    # Seed bag + strap.
    "bag_size": (0.15, 0.10, 0.17),   # full x, y, z extents
    "bag_height_ratio": 0.24,     # low enough for the strap to read as a diagonal
    "bag_embed": 0.35,            # fraction of bag x-extent overlapping the flank
    "strap_width": 0.05,          # across the band
    "strap_depth": 0.10,          # through the body, so the band stays visible
    "strap_shoulder_ratio": 0.70,
    "strap_shoulder_offset": 0.30,   # fraction of the body radius at shoulder height
    # Preview only (never exported to GLB).
    "preview_pitch_deg": 50.0,    # camera tilt below the horizon
    "preview_distance": 3.0,      # orthographic: affects clipping/placement, not scale
    "preview_margin": 1.25,       # empty border around the figure
    "preview_resolution": (768, 1024),
    # Colors (matte, texture-free).
    "colors": {
        "skin_cream": (0.93, 0.87, 0.74, 1.0),
        "cap_moss": (0.29, 0.42, 0.24, 1.0),
        "feet_brown": (0.24, 0.16, 0.10, 1.0),
        "eyes_dark": (0.05, 0.05, 0.06, 1.0),
        "bag_ochre": (0.72, 0.51, 0.20, 1.0),
        "strap_ochre_dark": (0.55, 0.38, 0.15, 1.0),
        "preview_ground": (0.55, 0.50, 0.42, 1.0),
    },
}

COLLECTION_NAME = "GardenWight_Character"
PREVIEW_COLLECTION_NAME = "GardenWight_PreviewSetup"
BLENDER_API_TARGET = (
    "4.5 LTS (assumed provisional baseline - verify bpy.app.version "
    "against the Blender actually installed before trusting API details)"
)

# The character faces -Y; the preview camera sits on that same side.
FRONT_SIGN = -1.0

# Radius of the source sphere the body is deformed from.
SPHERE_RADIUS = 0.5


# ---------------------------------------------------------------------------
# Pure geometry - no bpy, so these can be checked outside Blender.
# ---------------------------------------------------------------------------

def _pear_radius_factor(t: float) -> float:
    """Extra taper applied on top of the source sphere at height fraction t.

    Produces a rounded belly around t~0.4 and a gentle pinch near the
    neck (t~0.62), so the head reads as a smaller lobe on top of the
    body without a hard seam ("Kopf und Rumpf gehen optisch ineinander
    über").
    """
    t = min(max(t, 0.0), 1.0)
    belly = math.sin(t * math.pi) ** 0.7
    neck_pinch = 1.0 - 0.25 * math.exp(-((t - 0.62) ** 2) / 0.012)
    return max(belly * neck_pinch, 0.08)


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
    dims["hand_x"] = hand_r + config["hand_diameter"] * (0.5 - config["hand_embed"])
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

    # Strap: straight band from the opposite shoulder down to the bag's top,
    # laid over the front of the chest. Endpoints are exact; the band is a
    # simple box, so it grazes/intersects the curved chest in between.
    shoulder_z = _height_at(config, config["strap_shoulder_ratio"])
    shoulder_r = body_radius_at(shoulder_z, config)
    start_x = -bag_sign * shoulder_r * config["strap_shoulder_offset"]
    end_x = dims["bag_center"][0]
    end_z = dims["bag_top_z"]
    delta_x = end_x - start_x
    delta_z = end_z - shoulder_z
    dims["strap_start"] = (start_x, shoulder_z)
    dims["strap_end"] = (end_x, end_z)
    dims["strap_length"] = math.hypot(delta_x, delta_z)
    # Box' local +Z runs along the band: rotating by this angle about Y maps
    # (0, 0, 1) onto the normalised (delta_x, 0, delta_z).
    dims["strap_angle_y"] = math.atan2(delta_x, delta_z)
    dims["strap_y"] = FRONT_SIGN * min(shoulder_r, bag_r) * 0.80
    dims["strap_center"] = (
        (start_x + end_x) / 2.0,
        dims["strap_y"],
        (shoulder_z + end_z) / 2.0,
    )
    dims["body_radius_at_shoulder"] = shoulder_r

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


def _shade_smooth(mesh) -> None:
    for poly in mesh.polygons:
        poly.use_smooth = True


def get_or_create_material(name: str, rgba):
    """Flat, matte Principled BSDF material - no external textures."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
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


def _add_unit_sphere(name: str, extents, location, rotation=(0.0, 0.0, 0.0)):
    """Unit-diameter UV sphere scaled to full ``extents`` (x, y, z)."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=SPHERE_RADIUS, segments=16, ring_count=10)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = extents
    obj.location = location
    obj.rotation_euler = rotation
    _shade_smooth(obj.data)
    return obj


def _add_unit_box(name: str, extents, location, rotation=(0.0, 0.0, 0.0)):
    """Unit-edge cube scaled to full ``extents`` (x, y, z)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = extents
    obj.location = location
    obj.rotation_euler = rotation
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
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=18, radius=SPHERE_RADIUS)

    xy_scale = body_xy_scale(config)
    height_scale = config["body_height"] / (2.0 * SPHERE_RADIUS)
    for vert in bm.verts:
        t = (vert.co.z + SPHERE_RADIUS) / (2.0 * SPHERE_RADIUS)
        radial = _pear_radius_factor(t) * xy_scale
        vert.co.x *= radial
        vert.co.y *= radial
        vert.co.z *= height_scale

    mesh = bpy.data.meshes.new("Body_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    _shade_smooth(mesh)
    mesh.update()

    obj = bpy.data.objects.new("Body", mesh)
    obj.location = (0.0, 0.0, dims["body_center_z"])
    obj.data.materials.append(get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"]))
    return obj


def build_feet(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_FeetBrown", config["colors"]["feet_brown"])
    feet = []
    for side, sign in (("L", -1.0), ("R", 1.0)):
        obj = _add_unit_sphere(
            f"Foot.{side}",
            extents=(config["foot_width"], config["foot_length"], config["foot_height"]),
            location=(sign * dims["foot_x"], dims["foot_y"], dims["foot_center_z"]),
        )
        obj.data.materials.append(material)
        feet.append(obj)
    return feet


def build_hands(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"])
    hands = []
    for side, sign in (("L", -1.0), ("R", 1.0)):
        obj = _add_unit_sphere(
            f"Hand.{side}",
            extents=(config["hand_diameter"], config["hand_diameter"], config["hand_length"]),
            location=(sign * dims["hand_x"], 0.0, dims["hand_z"]),
            # Relaxed pose: the stubs lean outwards, away from the body.
            rotation=(0.0, sign * math.radians(config["hand_angle_deg"]), 0.0),
        )
        obj.data.materials.append(material)
        hands.append(obj)
    return hands


def build_eyes(config: dict, dims: dict) -> list:
    material = get_or_create_material("Mat_EyesDark", config["colors"]["eyes_dark"])
    diameter = config["eye_diameter"]
    eyes = []
    for side, sign in (("L", -1.0), ("R", 1.0)):
        obj = _add_unit_sphere(
            f"Eye.{side}",
            extents=(diameter, diameter, diameter),
            location=(sign * dims["eye_x"], dims["eye_y"], dims["eye_z"]),
        )
        obj.data.materials.append(material)
        eyes.append(obj)
    return eyes


def build_cap(config: dict, dims: dict):
    """Asymmetric moss-green leaf cap with a folded-over tip.

    The cone's mesh is shifted so the object origin sits at the brim,
    which makes ``cap_lean_deg`` rotate the cap around its base instead
    of around its middle.
    """
    bpy.ops.mesh.primitive_cone_add(
        radius1=config["cap_base_diameter"] / 2.0,
        radius2=0.0,
        depth=config["cap_height"],
        vertices=20,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.active_object
    obj.name = "Cap"
    obj.data.transform(Matrix.Translation((0.0, 0.0, config["cap_height"] / 2.0)))
    obj.location = (0.0, 0.0, dims["cap_base_z"])
    obj.rotation_euler = (0.0, math.radians(config["cap_lean_deg"]), 0.0)

    fold = obj.modifiers.new("Fold", type='SIMPLE_DEFORM')
    fold.deform_method = 'BEND'
    fold.deform_axis = 'X'          # bends the tip towards +/-Y (front/back)
    fold.angle = math.radians(config["cap_bend_deg"])
    fold.limits = (0.55, 1.0)       # only the upper part of the tip folds

    _shade_smooth(obj.data)
    obj.data.materials.append(get_or_create_material("Mat_CapMoss", config["colors"]["cap_moss"]))
    return obj


def build_bag_and_strap(config: dict, dims: dict) -> tuple:
    bag = _add_unit_box("Bag", extents=config["bag_size"], location=dims["bag_center"])
    bevel = bag.modifiers.new("SoftEdges", type='BEVEL')
    bevel.width = 0.015
    bevel.segments = 2
    bag.data.materials.append(get_or_create_material("Mat_BagOchre", config["colors"]["bag_ochre"]))

    strap = _add_unit_box(
        "Strap",
        extents=(config["strap_width"], config["strap_depth"], dims["strap_length"]),
        location=dims["strap_center"],
        rotation=(0.0, dims["strap_angle_y"], 0.0),
    )
    strap.data.materials.append(
        get_or_create_material("Mat_StrapOchreDark", config["colors"]["strap_ochre_dark"])
    )
    return bag, strap


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


# ---------------------------------------------------------------------------
# Export / preview / render
# ---------------------------------------------------------------------------

def export_glb(filepath: Path, collection) -> None:
    """Export only the character (geometry + materials) as GLB.

    Called before the preview setup exists, so no camera, light or
    ground plane can leak into the file.
    """
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection.all_objects:
        obj.select_set(True)
    mesh_objects = [obj for obj in collection.all_objects if obj.type == 'MESH']
    if mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]

    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format='GLB',
        use_selection=True,
        export_apply=True,       # bake modifiers (cap fold, bag bevel)
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

    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "Preview_Ground"
    ground.data.materials.append(
        get_or_create_material("Mat_PreviewGround", config["colors"]["preview_ground"])
    )
    _link_only(ground, preview_coll)

    bpy.ops.object.camera_add(location=dims["camera_location"])
    camera = bpy.context.active_object
    camera.name = "Preview_Camera"
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = dims["camera_ortho_scale"]
    camera.rotation_euler = dims["camera_rotation"]
    _link_only(camera, preview_coll)

    bpy.ops.object.light_add(
        type='SUN',
        location=(1.5, FRONT_SIGN * 1.5, dims["total_height"] + 1.5),
    )
    sun = bpy.context.active_object
    sun.name = "Preview_Sun"
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
    the most portable still-image path across Blender 4.x installs.
    """
    res_x, res_y = config["preview_resolution"]
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output_path)


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

    print(f"[garden_wight] Blender API target: {BLENDER_API_TARGET}")
    print(f"[garden_wight] Output directory: {output_dir}")

    dims = derive_dimensions(CONFIG)
    clear_scene()

    char_coll, _root = build_character(CONFIG, dims)
    report_bounding_height(char_coll, dims, CONFIG)

    glb_path = output_dir / "garden_wight.glb"
    export_glb(glb_path, char_coll)
    print(f"[garden_wight] Exported GLB (figure only, no camera/light/ground): {glb_path}")

    build_preview_setup(CONFIG, dims)

    png_path = output_dir / "garden_wight_preview.png"
    configure_render(bpy.context.scene, CONFIG, png_path)

    blend_path = output_dir / "garden_wight.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[garden_wight] Saved preview .blend (character + preview setup): {blend_path}")

    if args.render:
        bpy.ops.render.render(write_still=True)
        print(f"[garden_wight] Rendered preview PNG: {png_path}")


if __name__ == "__main__":
    main()
