"""Garden Wight character generator (Spirit Village).

Generates the first static version of the game's non-human player
character: a small, pear-shaped garden gnome ("Gartenwicht") with a
cream overcoat, an asymmetric moss-green leaf cap, dark round eyes, two
short rounded hand-stubs, two small dark-brown feet, and an ochre seed
bag on a diagonal strap.

IMPORTANT - environment assumption
-----------------------------------
This script only runs inside Blender's own Python (``bpy``/``bmesh`` are
not installed packages; they only exist inside a running Blender
process). It targets the **Blender 4.5 LTS** Python/glTF API as a
provisional baseline. The Blender version actually installed on the
artist's machine has not been confirmed yet - verify
``bpy.app.version`` against 4.5 before relying on API details here, and
adjust if it differs (see art/README.md).

Scene assumption
-----------------
The script assumes it is launched as a **separate Blender background
process with a factory-startup scene** (see the example command at the
bottom of this file and in art/README.md). ``clear_scene()`` wipes
every object, collection, mesh and material it finds, so this must
never be run against an artist's already-open working file.

Usage (inside Blender, arguments after ``--``)
-----------------------------------------------
    blender --background --factory-startup --python \\
        art/generators/garden_wight.py -- \\
        --output-dir build/characters/garden_wight [--render]

See art/README.md for the full command line, including notes on
locating the Blender executable, and for the list of things that still
need visual verification once this is actually run.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    import bpy
    import bmesh
except ImportError as exc:  # pragma: no cover - only happens outside Blender
    sys.exit(
        "garden_wight.py must be run from inside Blender, e.g.:\n"
        "  blender --background --factory-startup --python "
        "art/generators/garden_wight.py -- --output-dir <dir>\n"
        "It cannot be run with a plain system Python interpreter.\n"
        f"(original import error: {exc})"
    )


# ---------------------------------------------------------------------------
# Configuration - the single place to tune the character's shape and colors.
# All lengths are in Blender units; the whole figure targets roughly 1 unit
# of total height (feet to cap tip), per the design brief.
# ---------------------------------------------------------------------------

CONFIG = {
    # Overall proportions.
    "total_height_target": 1.0,   # documentation/reference only, not enforced
    "body_width": 0.60,           # max diameter of the pear-shaped body/head
    "body_height": 0.66,          # height of the body+head blob, feet/cap excluded
    "feet_height": 0.05,
    "feet_radius": 0.12,
    "feet_spacing": 0.17,
    # Hands (short rounded stubs, no fingers).
    "hand_radius": 0.075,
    "hand_length": 0.16,
    "hand_height_ratio": 0.55,    # fraction up body_height where hands attach
    "hand_spread": 0.34,          # horizontal offset from center
    # Eyes.
    "eye_height_ratio": 0.86,     # fraction up body_height, kept clear of the cap
    "eye_spacing": 0.15,
    "eye_radius": 0.035,
    # Cap (asymmetric, folded tip).
    "cap_base_radius": 0.34,
    "cap_height": 0.30,
    "cap_tilt_deg": 16.0,
    "cap_bend_deg": 55.0,         # folds the upper part of the tip over
    # Seed bag + strap.
    "bag_size": (0.15, 0.06, 0.17),   # x, y, z dimensions
    "bag_height_ratio": 0.40,
    "strap_width": 0.045,
    # Colors (linear-ish sRGB RGBA, matte look).
    "colors": {
        "skin_cream": (0.93, 0.87, 0.74, 1.0),
        "cap_moss": (0.29, 0.42, 0.24, 1.0),
        "feet_brown": (0.24, 0.16, 0.10, 1.0),
        "eyes_dark": (0.05, 0.05, 0.06, 1.0),
        "bag_ochre": (0.72, 0.51, 0.20, 1.0),
        "strap_ochre_dark": (0.55, 0.38, 0.15, 1.0),
    },
}

COLLECTION_NAME = "GardenWight_Character"
PREVIEW_COLLECTION_NAME = "GardenWight_PreviewSetup"
BLENDER_API_TARGET = (
    "4.5 LTS (assumed provisional baseline - verify bpy.app.version "
    "against the Blender actually installed before trusting API details)"
)

# Character "front" faces +Y; the preview camera looks back along -Y.
FRONT_SIGN = 1.0


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _link_only(obj: "bpy.types.Object", collection: "bpy.types.Collection") -> None:
    """Make ``collection`` the only collection ``obj`` is linked into."""
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)


def _shade_smooth(mesh: "bpy.types.Mesh") -> None:
    for poly in mesh.polygons:
        poly.use_smooth = True


def get_or_create_material(name: str, rgba) -> "bpy.types.Material":
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


def _pear_radius_factor(t: float) -> float:
    """Relative XY radius at height fraction ``t`` (0 = base, 1 = crown).

    Produces a rounded belly around t~0.35 and a gentle pinch near the
    neck (t~0.62) so the head reads as a smaller lobe on top of the
    body without a hard seam, matching the "Kopf und Rumpf gehen
    optisch ineinander über" design requirement.
    """
    t = min(max(t, 0.0), 1.0)
    belly = math.sin(t * math.pi) ** 0.7
    neck_pinch = 1.0 - 0.25 * math.exp(-((t - 0.62) ** 2) / 0.012)
    return max(belly * neck_pinch, 0.08)


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

def clear_scene() -> None:
    """Wipe the factory-startup scene down to nothing.

    Destructive by design - see the module docstring's "Scene
    assumption" section for why this script must only run in a
    dedicated background process, never against an open working file.
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


# ---------------------------------------------------------------------------
# Body parts
# ---------------------------------------------------------------------------

def build_body(config: dict) -> "bpy.types.Object":
    """Pear-shaped body+head blob, doubling as the cream overcoat.

    Design note: the brief's "cremefarbener kurzer Überwurf" is not
    modeled as a separate garment mesh for this first static pass -
    the body mesh itself *is* the visible cream overcoat surface, kept
    as a single, simple shape (see art/README.md).
    """
    sphere_radius = 0.5
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=18, radius=sphere_radius)

    width_scale = config["body_width"] / sphere_radius
    height_scale = config["body_height"] / (2 * sphere_radius)
    for v in bm.verts:
        t = (v.co.z + sphere_radius) / (2 * sphere_radius)
        radial = _pear_radius_factor(t) * width_scale
        v.co.x *= radial
        v.co.y *= radial
        v.co.z *= height_scale

    mesh = bpy.data.meshes.new("Body_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    _shade_smooth(mesh)
    mesh.update()

    obj = bpy.data.objects.new("Body", mesh)
    obj.location.z = config["feet_height"] + config["body_height"] / 2.0
    obj.data.materials.append(get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"]))
    return obj


def build_feet(config: dict) -> list:
    feet = []
    for side, sign in (("L", -1.0), ("R", 1.0)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=config["feet_radius"], segments=16, ring_count=10)
        obj = bpy.context.active_object
        obj.name = f"Foot.{side}"
        obj.scale = (1.0, 1.25, 0.6)
        obj.location = (sign * config["feet_spacing"] / 2.0, 0.02, config["feet_height"] * 0.55)
        _shade_smooth(obj.data)
        obj.data.materials.append(get_or_create_material("Mat_FeetBrown", config["colors"]["feet_brown"]))
        feet.append(obj)
    return feet


def build_hands(config: dict) -> list:
    hands = []
    hand_z = config["feet_height"] + config["body_height"] * config["hand_height_ratio"]
    for side, sign in (("L", -1.0), ("R", 1.0)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=config["hand_radius"], segments=14, ring_count=10)
        obj = bpy.context.active_object
        obj.name = f"Hand.{side}"
        obj.scale = (1.0, 1.0, config["hand_length"] / config["hand_radius"] / 2.0)
        # Relaxed pose: stubs angled slightly outward and down from the body.
        obj.rotation_euler = (math.radians(sign * -25.0), math.radians(15.0), 0.0)
        obj.location = (sign * config["hand_spread"], 0.0, hand_z)
        _shade_smooth(obj.data)
        obj.data.materials.append(get_or_create_material("Mat_SkinCream", config["colors"]["skin_cream"]))
        hands.append(obj)
    return hands


def build_eyes(config: dict) -> list:
    eyes = []
    eye_z = config["feet_height"] + config["body_height"] * config["eye_height_ratio"]
    eye_y = FRONT_SIGN * config["body_width"] * 0.42
    for side, sign in (("L", -1.0), ("R", 1.0)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=config["eye_radius"], segments=10, ring_count=8)
        obj = bpy.context.active_object
        obj.name = f"Eye.{side}"
        obj.location = (sign * config["eye_spacing"] / 2.0, eye_y, eye_z)
        _shade_smooth(obj.data)
        obj.data.materials.append(get_or_create_material("Mat_EyesDark", config["colors"]["eyes_dark"]))
        eyes.append(obj)
    return eyes


def build_cap(config: dict) -> "bpy.types.Object":
    """Asymmetric moss-green leaf cap with a folded-over tip.

    The base radius is deliberately kept a bit smaller than the head's
    own width so it does not fully occlude the eyes when viewed from
    the game's oblique top-down camera - see art/README.md's review
    notes for confirming this on the first real render.
    """
    cap_z = config["feet_height"] + config["body_height"] * 0.80
    bpy.ops.mesh.primitive_cone_add(
        radius1=config["cap_base_radius"],
        radius2=0.0,
        depth=config["cap_height"],
        vertices=20,
        location=(0.0, 0.0, cap_z + config["cap_height"] / 2.0),
    )
    obj = bpy.context.active_object
    obj.name = "Cap"

    bend = obj.modifiers.new("Fold", type='SIMPLE_DEFORM')
    bend.deform_method = 'BEND'
    bend.deform_axis = 'X'
    bend.angle = math.radians(config["cap_bend_deg"])
    bend.limits = (0.55, 1.0)  # only the upper part of the tip folds over

    obj.rotation_euler = (0.0, 0.0, math.radians(config["cap_tilt_deg"]))
    _shade_smooth(obj.data)
    obj.data.materials.append(get_or_create_material("Mat_CapMoss", config["colors"]["cap_moss"]))
    return obj


def build_bag_and_strap(config: dict) -> tuple:
    bag_x, bag_y, bag_z = config["bag_size"]
    bag_height_z = config["feet_height"] + config["body_height"] * config["bag_height_ratio"]
    # Bag sits on the side opposite the cap's tilt, for visual balance.
    bag_sign = -1.0 if config["cap_tilt_deg"] >= 0 else 1.0
    bag_x_pos = bag_sign * config["body_width"] * 0.52

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(bag_x_pos, 0.0, bag_height_z))
    bag = bpy.context.active_object
    bag.name = "Bag"
    bag.scale = (bag_x / 2.0, bag_y / 2.0, bag_z / 2.0)
    bevel = bag.modifiers.new("SoftEdges", type='BEVEL')
    bevel.width = 0.015
    bevel.segments = 2
    _shade_smooth(bag.data)
    bag.data.materials.append(get_or_create_material("Mat_BagOchre", config["colors"]["bag_ochre"]))

    # Diagonal strap from the opposite shoulder down to the bag; a thin
    # straight band is an approximation of the body's curve at this
    # stage (see art/README.md review notes).
    shoulder_z = config["feet_height"] + config["body_height"] * 0.92
    strap_length = math.dist((0.0, shoulder_z), (bag_x_pos, bag_height_z))
    strap_angle = math.atan2(bag_x_pos - 0.0, shoulder_z - bag_height_z)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(bag_x_pos / 2.0, -config["body_width"] * 0.36, (shoulder_z + bag_height_z) / 2.0),
    )
    strap = bpy.context.active_object
    strap.name = "Strap"
    strap.scale = (config["strap_width"] / 2.0, config["strap_width"] / 2.0, strap_length / 2.0)
    strap.rotation_euler = (0.0, -strap_angle, 0.0)
    _shade_smooth(strap.data)
    strap.data.materials.append(get_or_create_material("Mat_StrapOchreDark", config["colors"]["strap_ochre_dark"]))

    return bag, strap


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_character(config: dict):
    char_coll = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(char_coll)

    root = bpy.data.objects.new("GardenWight_Root", None)
    root.empty_display_size = 0.1
    char_coll.objects.link(root)

    parts = [build_body(config)]
    parts.extend(build_feet(config))
    parts.extend(build_hands(config))
    parts.extend(build_eyes(config))
    parts.append(build_cap(config))
    bag, strap = build_bag_and_strap(config)
    parts.extend((bag, strap))

    for obj in parts:
        _link_only(obj, char_coll)
        obj.parent = root

    return char_coll, root


def report_bounding_height(collection: "bpy.types.Collection", config: dict) -> None:
    """Print the assembled figure's actual world-space height.

    Useful, cheap feedback the first time this is run in real
    Blender: compares against ``total_height_target`` without
    asserting or failing the run, since exact proportions are meant to
    be tuned visually (see art/README.md).
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    min_z = math.inf
    max_z = -math.inf
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        eval_obj = obj.evaluated_get(depsgraph)
        for corner in eval_obj.bound_box:
            world_z = (eval_obj.matrix_world @ bpy_vector(corner)).z
            min_z = min(min_z, world_z)
            max_z = max(max_z, world_z)
    if min_z is math.inf:
        return
    height = max_z - min_z
    print(
        f"[garden_wight] Assembled height: {height:.3f} Blender units "
        f"(target ~{config['total_height_target']:.2f}, ground at {min_z:.3f})"
    )


def bpy_vector(coord):
    from mathutils import Vector
    return Vector(coord)


# ---------------------------------------------------------------------------
# Export / save / render
# ---------------------------------------------------------------------------

def export_glb(filepath: Path, collection: "bpy.types.Collection") -> None:
    """Export only the character (mesh geometry + materials) as GLB.

    No camera, light or ground plane exists in the scene yet at the
    point this is called (see main()'s call order), so a plain
    "select everything in the character collection" is sufficient to
    satisfy the "figure only" requirement.
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
        export_apply=True,       # bake modifiers (e.g. the cap's bend, bag bevel)
        export_materials='EXPORT',
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def build_preview_setup(config: dict):
    """Ground plane, soft sun light and an orthographic top-down-ish
    camera. Only used for the local .blend preview - never exported to
    GLB (see export_glb(), which runs before this is called).
    """
    preview_coll = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
    bpy.context.scene.collection.children.link(preview_coll)

    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "Preview_Ground"
    ground.data.materials.append(get_or_create_material("Mat_PreviewGround", (0.55, 0.50, 0.42, 1.0)))
    _link_only(ground, preview_coll)

    camera_tilt_deg = 50.0  # "etwa 50 Grad nach unten geneigt" from the brief
    bpy.ops.object.camera_add(location=(0.0, -1.9, 1.6))
    camera = bpy.context.active_object
    camera.name = "Preview_Camera"
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.6
    camera.rotation_euler = (math.radians(90.0 - camera_tilt_deg), 0.0, 0.0)
    _link_only(camera, preview_coll)

    bpy.ops.object.light_add(type='SUN', location=(1.5, -1.5, 2.5))
    sun = bpy.context.active_object
    sun.name = "Preview_Sun"
    sun.data.energy = 2.5
    sun.data.angle = math.radians(20.0)  # wide angle -> soft shadow edges
    _link_only(sun, preview_coll)

    bpy.context.scene.camera = camera
    return camera, ground


def configure_render(scene, output_path: Path) -> None:
    """Cycles on CPU: chosen because this pipeline assumes no guaranteed
    GPU is available wherever the render is actually produced (e.g. a
    headless CI box), and Cycles' CPU device path is the most portable
    still-image renderer across Blender 4.x installs. Document/replace
    with GPU (OPTIX/CUDA/HIP) explicitly if the target machine has one
    and faster iteration is needed.
    """
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1024
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
            "the current working directory Blender was launched from. "
            "Default: build/characters/garden_wight"
        ),
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also render a PNG preview (orthographic, ~50 degree top-down tilt).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[garden_wight] Blender API target: {BLENDER_API_TARGET}")
    print(f"[garden_wight] Output directory: {output_dir}")

    clear_scene()

    char_coll, root = build_character(CONFIG)
    report_bounding_height(char_coll, CONFIG)

    glb_path = output_dir / "garden_wight.glb"
    export_glb(glb_path, char_coll)
    print(f"[garden_wight] Exported GLB (figure only, no camera/light/ground): {glb_path}")

    build_preview_setup(CONFIG)

    blend_path = output_dir / "garden_wight.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[garden_wight] Saved preview .blend (character + preview setup): {blend_path}")

    if args.render:
        png_path = output_dir / "garden_wight_preview.png"
        configure_render(bpy.context.scene, png_path)
        bpy.ops.render.render(write_still=True)
        print(f"[garden_wight] Rendered preview PNG: {png_path}")


if __name__ == "__main__":
    main()
