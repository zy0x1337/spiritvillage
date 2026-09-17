"""Asset lineup renders (Spirit Village, art/PIPELINE.md session S3).

Places candidate GLBs in one row on a 1 m checker ground and renders them with
the game camera (orthographic, 50 degrees down, looking from the asset front)
and the game light (same values as ``art/generators/bldg_cottage.py``, which
match ``game/scenes/garden.tscn``). Renders use the S1 camera pixel density
(18 m of height on 800 logical px), so the images show the sizes a phone shows.

Usage (arguments after ``--``)::

    blender --background --factory-startup --python-exit-code 1 --python \\
        art/tools/lineup.py -- --output-dir build/lineup

Output: ``lineup_row_<n>x.png`` (all candidates) and ``lineup_figures_<n>x.png``
(characters next to a crop and a prop), plus one line per
candidate with height, footprint, triangles and pixel height at 1x.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "art" / "generators"))
import bldg_cottage as cottage  # noqa: E402  (camera helper, light and colour values)

# (label, GLB relative to the repo), left to right.
CANDIDATES = (
    ("crop_carrot_1", "game/assets/crops/crop_carrot_1.glb"),
    ("crop_carrot_2", "game/assets/crops/crop_carrot_2.glb"),
    ("crop_carrot_3", "game/assets/crops/crop_carrot_3.glb"),
    ("crop_carrot_4", "game/assets/crops/crop_carrot_4.glb"),
    ("crop_carrot_crop", "game/assets/crops/crop_carrot_crop.glb"),
    ("prop_barrel", "game/assets/props/prop_barrel.glb"),
    ("char_garden_wight", "game/assets/characters/char_garden_wight.glb"),
    ("char_forest_spirit", "game/assets/characters/char_forest_spirit.glb"),
    ("char_mushnub", "game/assets/characters/char_mushnub.glb"),
    ("bldg_cottage", "build/buildings/bldg_cottage/bldg_cottage.glb"),
    ("tree_common_1", "game/assets/nature/tree_common_1.glb"),
)
FIGURE_GROUP = ("crop_carrot_4", "prop_barrel", "char_garden_wight", "char_forest_spirit", "char_mushnub")

CELL_GAP = 0.3            # minimum free space between footprints (m)
PITCH_DEG = 50.0
PX_PER_M = 800.0 / 18.0   # S1 camera: 18 m vertical extent on 800 logical px
ROW_SCALES = (1, 3)       # 3 ~ a 1080 px wide phone
FIGURE_SCALES = (1, 1.5, 3)
GROUND = ((0.42, 0.30, 0.20, 1.0), (0.47, 0.34, 0.23, 1.0))  # sRGB, garden.tscn ground +/- a step


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def import_glb(path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def world_bounds(objects) -> tuple:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    tris = 0
    for obj in objects:
        if obj.type != 'MESH' or not obj.visible_get():  # skip importer helpers (bone shapes)
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        tris += sum(len(p.vertices) - 2 for p in mesh.polygons)
        for vert in mesh.vertices:
            co = evaluated.matrix_world @ vert.co
            lo = Vector(map(min, lo, co))
            hi = Vector(map(max, hi, co))
        evaluated.to_mesh_clear()
    return lo, hi, tris


def build_ground(x_min: float, x_max: float) -> None:
    mesh = bpy.data.meshes.new("Lineup_Ground")
    y0, y1 = -6.0, 6.0
    mesh.from_pydata([(x_min, y0, 0.0), (x_max, y0, 0.0), (x_max, y1, 0.0), (x_min, y1, 0.0)], [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.new("Lineup_Ground")
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Roughness"].default_value = 1.0
    coords = nodes.new("ShaderNodeTexCoord")
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 1.0  # 1 m squares (object coordinates, origin at 0)
    checker.inputs["Color1"].default_value = cottage.srgb_to_linear(GROUND[0])
    checker.inputs["Color2"].default_value = cottage.srgb_to_linear(GROUND[1])
    links.new(coords.outputs["Object"], checker.inputs["Vector"])
    links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(mat)
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("Lineup_Ground", mesh))


def setup_light_and_camera():
    config = cottage.CONFIG
    sun = bpy.data.objects.new("Lineup_Sun", bpy.data.lights.new("Lineup_Sun", type='SUN'))
    sun.data.energy = config["sun_strength"]
    sun.data.angle = math.radians(config["sun_angle_deg"])
    sun.rotation_euler = Vector(config["sun_direction"]).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(sun)

    world = bpy.context.scene.world or bpy.data.worlds.new("Lineup_World")
    bpy.context.scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    background = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if background is not None:
        background.inputs["Color"].default_value = cottage.srgb_to_linear(config["world_color"])
        background.inputs["Strength"].default_value = config["world_strength"]

    camera = bpy.data.objects.new("Lineup_Camera", bpy.data.cameras.new("Lineup_Camera"))
    camera.data.type = 'ORTHO'
    camera.data.sensor_fit = 'VERTICAL'
    camera.data.clip_end = 200.0
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    return camera


def pixel_height(scene, camera, objects) -> float:
    from bpy_extras.object_utils import world_to_camera_view

    depsgraph = bpy.context.evaluated_depsgraph_get()
    ys = []
    for obj in objects:
        if obj.type != 'MESH' or not obj.visible_get():
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        ys += [world_to_camera_view(scene, camera, evaluated.matrix_world @ v.co).y for v in mesh.vertices]
        evaluated.to_mesh_clear()
    return (max(ys) - min(ys)) * scene.render.resolution_y if ys else 0.0


def frame(scene, camera, x0: float, x1: float, y_front: float, y_back: float, top: float, density: float) -> None:
    """Camera over a ground rectangle (+ height ``top``) at ``density`` px per m."""
    pitch = math.radians(PITCH_DEG)
    target = ((x0 + x1) / 2.0, (y_front + y_back) / 2.0, top / 2.0)
    camera.location, camera.rotation_euler = cottage.orbit_camera(target, 0.0, PITCH_DEG, 60.0)
    height_m = (y_back - y_front) * math.sin(pitch) + top * math.cos(pitch)
    scene.render.resolution_x = round((x1 - x0) * density)
    scene.render.resolution_y = round(height_m * density)
    camera.data.ortho_scale = scene.render.resolution_y / density
    bpy.context.view_layer.update()


def render(scene, path: Path) -> None:
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[lineup] Rendered {path.name} ({scene.render.resolution_x}x{scene.render.resolution_y})")


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="lineup.py")
    parser.add_argument("--output-dir", default="build/lineup")
    args = parser.parse_args(argv)
    output_dir = (REPO / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()
    placed = {}
    x = 0.0
    for label, rel in CANDIDATES:
        path = REPO / rel
        if not path.exists():
            raise SystemExit(f"[lineup] missing {rel}")
        objects = import_glb(path)
        bpy.context.view_layer.update()
        lo, hi, tris = world_bounds(objects)
        width = hi.x - lo.x
        # Snap the footprint centre to the 1 m grid, leaving CELL_GAP to the neighbour.
        centre = math.ceil(x + width / 2.0 + CELL_GAP / 2.0 - 0.5) + 0.5
        for obj in objects:
            if obj.parent is None:
                obj.location.x += centre - (lo.x + hi.x) / 2.0
                obj.location.y -= (lo.y + hi.y) / 2.0
        x = centre + width / 2.0 + CELL_GAP / 2.0
        placed[label] = {"objects": objects, "height": hi.z - lo.z, "width": width,
                         "depth": hi.y - lo.y, "tris": tris, "min_z": lo.z}

    bpy.context.view_layer.update()
    build_ground(-1.0, x + 1.0)
    camera = setup_light_and_camera()
    scene = bpy.context.scene

    tallest = max(item["height"] for item in placed.values())
    deepest = max(item["depth"] for item in placed.values())
    frame(scene, camera, -0.5, x + 0.5, -deepest / 2.0 - 0.5, deepest / 2.0 + 0.5, tallest + 0.3, PX_PER_M)
    for label, item in placed.items():
        px = pixel_height(scene, camera, item["objects"])
        print(f"[lineup] {label:18s} height {item['height']:.3f} m, footprint {item['width']:.2f} x "
              f"{item['depth']:.2f} m, {item['tris']:5d} tris, min_z {item['min_z']:+.4f}, "
              f"{px:.0f} px at 1x ({px * 3:.0f} px at 3x)")
    for factor in ROW_SCALES:
        frame(scene, camera, -0.5, x + 0.5, -deepest / 2.0 - 0.5, deepest / 2.0 + 0.5, tallest + 0.3,
              PX_PER_M * factor)
        render(scene, output_dir / f"lineup_row_{factor}x.png")

    group = [placed[label] for label in FIGURE_GROUP]
    x0 = min(o.matrix_world.translation.x for g in group for o in g["objects"] if o.parent is None) - 0.9
    x1 = max(o.matrix_world.translation.x for g in group for o in g["objects"] if o.parent is None) + 1.2
    for factor in FIGURE_SCALES:
        frame(scene, camera, x0, x1, -1.2, 1.2, 1.4, PX_PER_M * factor)
        heights = ", ".join(
            f"{label} {pixel_height(scene, camera, placed[label]['objects']):.0f} px"
            for label in ("char_garden_wight", "char_forest_spirit", "char_mushnub"))
        print(f"[lineup] figures {factor}x: {heights}")
        render(scene, output_dir / f"lineup_figures_{str(factor).replace('.', '_')}x.png")


main()
