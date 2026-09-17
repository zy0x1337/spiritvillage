"""Inventory icon renders (Spirit Village, art/PIPELINE.md session S7).

Renders one 256 x 256 PNG with a transparent background per game GLB, all from
the same fixed three-quarter view and the same light as ``art/tools/lineup.py``
(orthographic camera via ``bldg_cottage.orbit_camera``, sun and world from
``bldg_cottage.CONFIG``, Cycles CPU). Each object is centred, framed from its
own bounding box (about 8 % border) and written to ``<output-dir>/<id>.png``.
A contact sheet of all rendered icons is written to
``docs/previews/icons_sheet.png``.

Usage (arguments after ``--``)::

    blender --background --factory-startup --python-exit-code 1 \\
      --python art/tools/render_icons.py -- [--output-dir game/assets/icons] [--only <id>]
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "art" / "generators"))
import bldg_cottage as cottage  # noqa: E402  (camera helper, light and colour values)

# (id, GLB relative to the repo), fixed order. char_mushnub is a comparison
# asset only and is not rendered.
ASSETS = (
    ("crop_carrot_1", "game/assets/crops/crop_carrot_1.glb"),
    ("crop_carrot_2", "game/assets/crops/crop_carrot_2.glb"),
    ("crop_carrot_3", "game/assets/crops/crop_carrot_3.glb"),
    ("crop_carrot_4", "game/assets/crops/crop_carrot_4.glb"),
    ("crop_carrot_crop", "game/assets/crops/crop_carrot_crop.glb"),
    ("prop_barrel", "game/assets/props/prop_barrel.glb"),
    ("bldg_cottage", "game/assets/buildings/bldg_cottage.glb"),
    ("bldg_oven", "game/assets/buildings/bldg_oven.glb"),
    ("char_garden_wight", "game/assets/characters/char_garden_wight.glb"),
    ("char_forest_spirit", "game/assets/characters/char_forest_spirit.glb"),
)

RESOLUTION = 256
MARGIN = 0.08          # free border on each side as a fraction of the icon
YAW_DEG = 30.0         # three-quarter view, front +Z turned 30 degrees
PITCH_DEG = 30.0       # camera looks down 30 degrees
SAMPLES = 64
SHEET_PATH = REPO / "docs" / "previews" / "icons_sheet.png"


def log(msg: str) -> None:
    print(msg, flush=True)


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def visible_meshes(objects: list) -> list:
    return [o for o in objects if o.type == "MESH" and o.visible_get()]


def world_bounds(meshes: list) -> tuple:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vert in mesh.vertices:
            co = evaluated.matrix_world @ vert.co
            lo = Vector(map(min, lo, co))
            hi = Vector(map(max, hi, co))
        evaluated.to_mesh_clear()
    return lo, hi


def center_objects(objects: list, lo: Vector, hi: Vector) -> None:
    delta = -(lo + hi) / 2.0
    for obj in objects:
        if obj.parent is None:
            obj.location = obj.location + delta
    bpy.context.view_layer.update()


def setup_light_and_world() -> None:
    config = cottage.CONFIG
    sun = bpy.data.objects.new("Icon_Sun", bpy.data.lights.new("Icon_Sun", type="SUN"))
    sun.data.energy = config["sun_strength"]
    sun.data.angle = math.radians(config["sun_angle_deg"])
    sun.rotation_euler = Vector(config["sun_direction"]).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(sun)

    world = bpy.data.worlds.new("Icon_World")
    bpy.context.scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    background = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if background is not None:
        background.inputs["Color"].default_value = cottage.srgb_to_linear(config["world_color"])
        background.inputs["Strength"].default_value = config["world_strength"]


def setup_camera(distance: float):
    camera = bpy.data.objects.new("Icon_Camera", bpy.data.cameras.new("Icon_Camera"))
    camera.data.type = "ORTHO"
    camera.data.sensor_fit = "AUTO"
    camera.data.clip_start = 0.01
    camera.data.clip_end = distance * 4.0 + 50.0
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location, camera.rotation_euler = cottage.orbit_camera(
        (0.0, 0.0, 0.0), YAW_DEG, PITCH_DEG, distance)
    return camera


def camera_bounds(camera, meshes: list) -> tuple:
    """Min/max of the meshes' vertices in camera space (x right, y up)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    to_camera = camera.matrix_world.inverted()
    xs, ys = [], []
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vert in mesh.vertices:
            co = to_camera @ (evaluated.matrix_world @ vert.co)
            xs.append(co.x)
            ys.append(co.y)
        evaluated.to_mesh_clear()
    return min(xs), max(xs), min(ys), max(ys)


def frame_object(camera, meshes: list) -> None:
    min_x, max_x, min_y, max_y = camera_bounds(camera, meshes)
    # Centre the projected bounding box, then fit it with MARGIN on each side.
    offset = camera.matrix_world.to_3x3() @ Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, 0.0))
    camera.location = camera.location + offset
    bpy.context.view_layer.update()
    extent = max(max_x - min_x, max_y - min_y)
    camera.data.ortho_scale = extent / (1.0 - 2.0 * MARGIN)


def configure_render() -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.seed = 0
    if hasattr(scene.cycles, "use_animated_seed"):
        scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = False
    # Fixed single thread and no adaptive sampling keep the output byte-identical
    # across runs (requirement: same input -> same output).
    scene.cycles.use_adaptive_sampling = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.render.film_transparent = True
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    # Do not embed volatile metadata (Date, RenderTime, per-render times) in the
    # PNG; otherwise two identical renders differ in bytes.
    scene.render.use_stamp = False
    for attr in (
        "use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame",
        "use_stamp_frame_range", "use_stamp_memory", "use_stamp_hostname", "use_stamp_camera",
        "use_stamp_lens", "use_stamp_scene", "use_stamp_marker", "use_stamp_filename",
        "use_stamp_sequencer_strip", "use_stamp_note", "use_stamp_labels",
    ):
        if hasattr(scene.render, attr):
            setattr(scene.render, attr, False)


def strip_png_metadata(path: Path) -> None:
    """Drop PNG text/time chunks so two identical renders are byte-identical."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return
    drop = {b"tEXt", b"zTXt", b"iTXt", b"tIME"}
    out = bytearray(data[:8])
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        total = 12 + length
        if chunk_type not in drop:
            out += data[offset:offset + total]
        offset += total
    path.write_bytes(out)


def opaque_fraction(path: Path) -> float:
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
    bpy.data.images.remove(image)
    return float(np.count_nonzero(pixels[..., 3] >= 0.5)) / float(RESOLUTION * RESOLUTION)


def render_icon(asset_id: str, source: Path, output_dir: Path) -> float:
    reset()
    objects = import_glb(source)
    meshes = visible_meshes(objects)
    if not meshes:
        raise SystemExit(f"[icons] {asset_id}: no visible mesh in {source}")
    lo, hi = world_bounds(meshes)
    center_objects(objects, lo, hi)
    lo, hi = world_bounds(meshes)
    distance = 4.0 * max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) + 3.0
    setup_light_and_world()
    camera = setup_camera(distance)
    frame_object(camera, meshes)
    configure_render()
    target = output_dir / f"{asset_id}.png"
    bpy.context.scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    strip_png_metadata(target)
    fraction = opaque_fraction(target)
    log(f"[icons] {asset_id}: {RESOLUTION}x{RESOLUTION} opaque={fraction * 100.0:.1f}% -> {target.name}")
    return fraction


def write_sheet(asset_ids: list, output_dir: Path) -> None:
    if not asset_ids:
        return
    width = RESOLUTION * len(asset_ids)
    sheet = np.ones((RESOLUTION, width, 4), dtype=np.float32)
    sheet[..., :3] = 0.86
    for column, asset_id in enumerate(asset_ids):
        path = output_dir / f"{asset_id}.png"
        image = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
        bpy.data.images.remove(image)
        alpha = pixels[..., 3:4]
        span = slice(column * RESOLUTION, (column + 1) * RESOLUTION)
        sheet[:, span, :3] = pixels[..., :3] * alpha + sheet[:, span, :3] * (1.0 - alpha)
    out = bpy.data.images.new("icons_sheet", width=width, height=RESOLUTION, alpha=True)
    out.colorspace_settings.name = "sRGB"
    out.pixels = sheet.reshape(-1).tolist()
    SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.filepath_raw = str(SHEET_PATH)
    out.file_format = "PNG"
    out.save()
    strip_png_metadata(SHEET_PATH)
    log(f"[icons] sheet {SHEET_PATH} ({width}x{RESOLUTION})")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="render_icons.py")
    parser.add_argument("--output-dir", default="game/assets/icons")
    parser.add_argument("--only", default=None)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    output_dir = (REPO / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = [(i, rel) for i, rel in ASSETS if args.only is None or i == args.only]
    if not assets:
        raise SystemExit(f"[icons] unknown --only id: {args.only}")
    log(f"[run] blender {bpy.app.version_string}, {len(assets)} asset(s)")
    for asset_id, rel in assets:
        source = REPO / rel
        if not source.exists():
            raise SystemExit(f"[icons] missing {rel}")
        render_icon(asset_id, source, output_dir)
    write_sheet([asset_id for asset_id, _ in assets], output_dir)


main()
