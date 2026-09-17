"""Asset intake for Spirit Village.

Blender background script. Reads art/intake_manifest.json, imports each source,
normalises it for the Godot project (1 m = 1 unit, origin at footprint centre,
ground contact at y = 0, no node scale, matte materials, textures <= 1024 px),
exports a GLB with embedded textures and rewrites art/ASSETS.md.

Usage (from the repository root):

    blender --background --factory-startup --python-exit-code 1 \
      --python art/tools/intake.py -- --manifest art/intake_manifest.json [--only <id>] [--verify]

Everything that needs to exist in a fresh scene is created per entry; geometry
is only touched through bpy.data, operators are used for import/export and for
transform application (see art/BLENDER_WORKFLOW.md section 1).
"""

import argparse
import datetime
import json
import math
import os
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

REPO_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_MAX_PX = 1024
DEFAULT_MATERIAL_ROUGHNESS = 0.9
DEFAULT_MATERIAL_METALLIC = 0.0
# Triangle budgets from art/PIPELINE.md section 7. None = report only.
BUDGETS = {
    "char": 10000,
    "crop": 1500,
    "tree": 4000,
    "bldg": 8000,
    "prop": None,
}
NOT_EXPORTED_COLLECTION = "glTF_not_exported"


def log(msg):
    print(msg, flush=True)


def fail(entry_id, message):
    log(f"FEHLER: {entry_id}: {message}")
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Manifest / paths
# --------------------------------------------------------------------------- #

def load_manifest(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    entries = data.get("entries")
    if not entries:
        raise ValueError("manifest contains no entries")
    return data, entries


def asset_source_base(manifest):
    env = manifest.get("asset_source_env", "SV_ASSET_SOURCE")
    value = os.environ.get(env)
    source = value if value else manifest.get("asset_source_default")
    log(f"[env] {env}={value!r} -> using {source!r}")
    return Path(source)


def resolve_source(entry, base):
    if entry.get("source_root", "assets") == "repo":
        return (REPO_ROOT / entry["source"]).resolve()
    return (base / entry["source"]).resolve()


def resolve_target(entry):
    return (REPO_ROOT / entry["target"]).resolve()


# --------------------------------------------------------------------------- #
# Scene helpers
# --------------------------------------------------------------------------- #

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_file(path):
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")
    if ext in ("gltf", "glb"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == "fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == "obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise ValueError(f"unsupported file extension: {ext}")


def in_not_exported(obj):
    return any(c.name == NOT_EXPORTED_COLLECTION for c in obj.users_collection)


def exportable_objects():
    return [o for o in bpy.data.objects if not in_not_exported(o)]


def is_skinned(obj):
    return obj.type == "MESH" and any(m.type == "ARMATURE" for m in obj.modifiers)


def evaluated_bbox(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e18, 1e18, 1e18))
    mx = Vector((-1e18, -1e18, -1e18))
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vert in mesh.vertices:
            world = evaluated.matrix_world @ vert.co
            mn = Vector((min(mn.x, world.x), min(mn.y, world.y), min(mn.z, world.z)))
            mx = Vector((max(mx.x, world.x), max(mx.y, world.y), max(mx.z, world.z)))
        evaluated.to_mesh_clear()
    return mn, mx


def mesh_stats(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    materials = set()
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
        for mat in obj.data.materials:
            if mat:
                materials.add(mat.name)
    return triangles, sorted(materials)


def apply_matrix(objects, matrix):
    for obj in objects:
        obj.matrix_world = matrix @ obj.matrix_world


def bake_transforms(objects):
    """Apply rotation and scale into data; skinned meshes keep their bind pose."""
    bpy.ops.object.select_all(action="DESELECT")
    selected = [o for o in objects if not is_skinned(o)]
    if not selected:
        return
    for obj in selected:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = selected[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


# --------------------------------------------------------------------------- #
# Materials and textures
# --------------------------------------------------------------------------- #

def override_for(material, material_map):
    if material.name in material_map:
        return material_map[material.name]
    base = material.name.split(".")[0]
    return material_map.get(base)


def simplify_material(material, material_map):
    node_tree = material.node_tree
    if node_tree is None:
        return
    bsdf = next((n for n in node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    for name in ("Normal", "Metallic", "Roughness", "Specular", "Specular IOR Level"):
        socket = bsdf.inputs.get(name)
        if socket:
            for link in list(socket.links):
                node_tree.links.remove(link)
    if bsdf.inputs.get("Metallic"):
        bsdf.inputs["Metallic"].default_value = DEFAULT_MATERIAL_METALLIC
    if bsdf.inputs.get("Roughness"):
        bsdf.inputs["Roughness"].default_value = DEFAULT_MATERIAL_ROUGHNESS
    override = override_for(material, material_map)
    if override and "base_color" in override:
        base = bsdf.inputs.get("Base Color")
        if base:
            for link in list(base.links):
                node_tree.links.remove(link)
            r, g, b = override["base_color"]
            base.default_value = (r, g, b, 1.0)
    # Drop the whole chain that fed the removed inputs (normal maps, ORM ...).
    # Only the surface output and the shader itself are always kept.
    always_keep = {"OUTPUT_MATERIAL", "BSDF_PRINCIPLED"}
    changed = True
    while changed:
        changed = False
        linked_from = {link.from_node.name for link in node_tree.links}
        for node in list(node_tree.nodes):
            if node.type in always_keep:
                continue
            if node.name not in linked_from:
                node_tree.nodes.remove(node)
                changed = True


def process_materials(material_map):
    for material in bpy.data.materials:
        simplify_material(material, material_map)


def used_images():
    images = set()
    for material in bpy.data.materials:
        node_tree = material.node_tree
        if node_tree is None:
            continue
        for node in node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images.add(node.image)
    return images


def shrink_textures(max_px=TEXTURE_MAX_PX):
    resized = []
    for image in used_images():
        width, height = image.size
        if width <= max_px and height <= max_px:
            continue
        if width >= height:
            new_w = max_px
            new_h = max(1, round(height * max_px / width))
        else:
            new_h = max_px
            new_w = max(1, round(width * max_px / height))
        image.scale(new_w, new_h)
        resized.append((image.name, new_w, new_h))
    return resized


# --------------------------------------------------------------------------- #
# Export / verification
# --------------------------------------------------------------------------- #

def export_glb(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_animations=True,
    )


def glb_node_scales(path):
    scales = []
    with open(path, "rb") as handle:
        magic, _version, _length = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF":
            raise ValueError(f"{path} is not a GLB file")
        chunk_length, _chunk_type = struct.unpack("<I4s", handle.read(8))
        document = json.loads(handle.read(chunk_length).decode("utf-8"))
    for node in document.get("nodes", []):
        scale = node.get("scale")
        if scale:
            scales.append((node.get("name", "?"), tuple(scale)))
    return scales


def count_animations(path):
    reset_scene()
    import_file(path)
    return len(bpy.data.actions)


# --------------------------------------------------------------------------- #
# Per-entry processing
# --------------------------------------------------------------------------- #

def process_entry(entry, base):
    entry_id = entry["id"]
    source = resolve_source(entry, base)
    target = resolve_target(entry)
    if not source.exists():
        fail(entry_id, f"source not found: {source}")

    reset_scene()
    try:
        import_file(source)
    except Exception as exc:  # noqa: BLE001 - report and abort the run
        fail(entry_id, f"import failed: {exc}")

    objects = exportable_objects()
    if not objects:
        fail(entry_id, "import produced no objects")
    roots = [o for o in objects if o.parent is None]
    source_animations = len(bpy.data.actions)

    rotation = entry.get("rotate_y_deg", 0) or 0
    if rotation:
        apply_matrix(roots, Matrix.Rotation(math.radians(rotation), 4, "Z"))

    scale = entry.get("scale")
    target_height = entry.get("target_height_m")
    if scale is None and target_height is None:
        fail(entry_id, "neither 'scale' nor 'target_height_m' given")

    if scale is not None:
        apply_matrix(roots, Matrix.Scale(float(scale), 4))
        bake_transforms(objects)
    else:
        for _attempt in range(6):
            mn, mx = evaluated_bbox(objects)
            height = mx.z - mn.z
            if height <= 0:
                fail(entry_id, "model has no height")
            if abs(height - target_height) / target_height <= 0.001:
                break
            apply_matrix(roots, Matrix.Scale(target_height / height, 4))
            bake_transforms(objects)
        mn, mx = evaluated_bbox(objects)
        if abs((mx.z - mn.z) - target_height) / target_height > 0.01:
            fail(entry_id, f"could not reach target height {target_height} m")

    # Footprint centred in X/Z, ground contact at y = 0 (glTF axes).
    bpy.context.view_layer.update()
    mn, mx = evaluated_bbox(objects)
    delta = Vector((-(mn.x + mx.x) / 2.0, -(mn.y + mx.y) / 2.0, -mn.z))
    for root in roots:
        root.location = root.location + delta
    bpy.context.view_layer.update()

    process_materials(entry.get("material_map") or {})
    resized = shrink_textures()

    triangles, materials = mesh_stats(objects)
    mn, mx = evaluated_bbox(objects)

    export_glb(target)
    exported_animations = count_animations(str(target))

    prefix = entry_id.split("_")[0]
    budget = BUDGETS.get(prefix)
    if budget is None:
        budget_text = "prop (kein Budget, nur Meldung)"
    else:
        budget_text = f"{prefix} <= {budget} " + ("OK" if triangles <= budget else "UEBER")

    log(
        f"[asset] {entry_id}: tris={triangles} materials={len(materials)}{materials} "
        f"bbox=({mn.x:.4f},{mn.y:.4f},{mn.z:.4f})-({mx.x:.4f},{mx.y:.4f},{mx.z:.4f}) "
        f"h={mx.z - mn.z:.4f} anims={source_animations}->{exported_animations} "
        f"textures_resized={resized} budget={budget_text}"
    )
    if budget is not None and triangles > budget:
        log(f"[warn] {entry_id}: triangle budget exceeded ({triangles} > {budget})")

    return {
        "entry": entry,
        "triangles": triangles,
        "materials": materials,
        "bbox_min": mn,
        "bbox_max": mx,
        "source_animations": source_animations,
        "exported_animations": exported_animations,
        "resized": resized,
        "budget": budget,
        "budget_text": budget_text,
    }


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #

def verify_entry(entry, base):
    entry_id = entry["id"]
    target = resolve_target(entry)
    if not target.exists():
        fail(entry_id, f"target missing: {target}")
    source = resolve_source(entry, base)

    source_animations = count_animations(str(source)) if source.exists() else 0
    reset_scene()
    import_file(str(target))
    objects = exportable_objects()
    mn, mx = evaluated_bbox(objects)
    exported_animations = len(bpy.data.actions)

    scales = glb_node_scales(str(target))
    bad_scales = [(name, s) for name, s in scales if any(abs(v - 1.0) > 1e-3 for v in s)]
    min_y_ok = abs(mn.z) <= 0.001
    center_ok = abs(mn.x + mx.x) / 2.0 <= 0.01 and abs(mn.y + mx.y) / 2.0 <= 0.01
    anims_ok = source_animations == exported_animations

    status = "PASS" if (min_y_ok and center_ok and not bad_scales and anims_ok) else "FAIL"
    log(
        f"[verify] {entry_id}: min_y={mn.z:+.4f} ({'ok' if min_y_ok else 'bad'}) "
        f"center_xz=({(mn.x + mx.x) / 2.0:+.4f},{(mn.y + mx.y) / 2.0:+.4f}) "
        f"({'ok' if center_ok else 'bad'}) "
        f"node_scales={scales if scales else 'none'} ({'ok' if not bad_scales else 'bad'}) "
        f"anims={source_animations}->{exported_animations} ({'ok' if anims_ok else 'bad'}) "
        f"=> {status}"
    )
    if status != "PASS":
        sys.exit(1)


# --------------------------------------------------------------------------- #
# Provenance file
# --------------------------------------------------------------------------- #

def changes_text(entry):
    parts = [f"Drehung {entry.get('rotate_y_deg', 0)}°"]
    if "scale" in entry:
        parts.append(f"Skalierung x{entry['scale']}")
    if "target_height_m" in entry:
        parts.append(f"Höhe auf {entry['target_height_m']} m")
    parts.append("Normal-/ORM-Texturen entfernt, metallic 0, roughness 0,9")
    material_map = entry.get("material_map") or {}
    if material_map:
        parts.append("Palettenfarben: " + ", ".join(sorted(material_map)))
    parts.append(f"Texturen <= {TEXTURE_MAX_PX} px")
    return ", ".join(parts)


def write_assets_md(results, base):
    today = datetime.date.today().isoformat()
    lines = [
        "# Asset-Herkunft",
        "",
        f"Erzeugt von `art/tools/intake.py` am {today}. Rohpakete liegen außerhalb "
        f"von Git unter `$SV_ASSET_SOURCE` (hier `{base}`); versioniert werden nur "
        "die verarbeiteten GLBs unter `game/assets/`.",
        "",
        "| Spieldatei | Id | Paket | Edition | Quelldatei | Lizenz | Änderungen | Dreiecke |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        entry = result["entry"]
        lines.append(
            "| `{target}` | `{id}` | {package} | {edition} | `{source}` | {license} | {changes} | {tris} |".format(
                target=entry["target"],
                id=entry["id"],
                package=entry["package"],
                edition=entry["edition"],
                source=entry["source"],
                license=entry["license"],
                changes=changes_text(entry),
                tris=result["triangles"],
            )
        )
    lines.append("")
    output = REPO_ROOT / "art" / "ASSETS.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    log(f"[provenance] wrote {output}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(prog="intake.py")
    parser.add_argument("--manifest", default="art/intake_manifest.json")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    manifest, entries = load_manifest(manifest_path)
    base = asset_source_base(manifest)

    if args.only:
        wanted = set(args.only)
        entries = [e for e in entries if e["id"] in wanted]
        missing = wanted - {e["id"] for e in entries}
        if missing:
            fail("manifest", f"unknown --only ids: {sorted(missing)}")

    log(f"[run] blender {bpy.app.version_string}, {len(entries)} entries, verify={args.verify}")

    if args.verify:
        for entry in entries:
            verify_entry(entry, base)
        log("[done] verify")
        return

    results = []
    for entry in entries:
        results.append(process_entry(entry, base))
    write_assets_md(results, base)
    log(f"[done] processed {len(results)} assets")


if __name__ == "__main__":
    main()
