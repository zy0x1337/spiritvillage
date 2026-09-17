"""Shared creature base for Spirit Village character generators.

Owns everything the rounded, non-human garden beings have in common:
the body silhouette (a sphere deformed by a radial profile), feet, hands,
eyes with catch-lights, node hierarchy and pivots, the automatic checks
(part intersections, vertex-measured height and ground contact, triangle
budget, GLB content), GLB export and the ``--views`` check renders.
Each creature is a thin module with a ``CONFIG`` block, its own parts and
a ``SPEC`` that is handed to :func:`run` (see ``garden_wight.py`` and
``forest_spirit.py``). Working rules: ``art/BLENDER_WORKFLOW.md``.

Conventions (shared by every creature)
--------------------------------------
* **Z-up**, foot soles exactly on ``z = 0``. The figure **faces -Y**; the
  glTF exporter maps that to glTF **+Z** (``Vector3.MODEL_FRONT`` in Godot).
  ``.L``/``.R`` follow Blender's mirror convention: the figure's left is +X.
* **Every size in CONFIG is a full extent** (diameter / length / width /
  height), never a radius; ratios are fractions of ``body_height`` measured
  from the body's lowest point. Sizes are baked into the mesh data, nodes
  carry only location and rotation.
* **Colours in CONFIG are sRGB** (what a colour picker shows) and are
  converted to linear for the Principled BSDF, like ``bldg_cottage.py``.

The ``bpy`` import is soft: the pure geometry helpers can be imported and
checked with a plain Python interpreter.
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import struct
import sys
from pathlib import Path

try:  # Blender-only modules
    import bpy
    import bmesh
    from mathutils import Euler, Matrix, Quaternion, Vector
except ImportError:  # pragma: no cover - outside Blender
    bpy = None
    bmesh = None
    Euler = Matrix = Quaternion = Vector = None

BLENDER_API_TARGET = "5.2.1 LTS (verified); older versions untested"

# The figure faces -Y; preview cameras sit on that same side.
FRONT_SIGN = -1.0

# Radius of the source sphere every round part is deformed from.
SPHERE_RADIUS = 0.5

# Catch-light direction on both eyes: up and towards the figure's right (-X).
EYE_SHINE_LIGHT = (-0.45, 0.0, 0.9)


# ---------------------------------------------------------------------------
# Pure geometry - no bpy, so these can be checked outside Blender.
# ---------------------------------------------------------------------------

def smoothstep(edge0: float, edge1: float, x: float) -> float:
    x = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def srgb_to_linear(rgba) -> tuple:
    """sRGB colour (0..1) -> linear, alpha unchanged (alpha defaults to 1)."""
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    rgba = tuple(rgba)
    return tuple(channel(c) for c in rgba[:3]) + (tuple(rgba[3:]) or (1.0,))


def _profile_keys(config: dict) -> tuple:
    lo, hi = config["body_taper_range"]
    return (config["body_taper"], lo, hi, config.get("body_bottom_fullness", 1.0))


def _radial_factor(t: float, taper: float, lo: float, hi: float, fullness: float) -> float:
    """Factor applied on top of the source sphere's own falloff at height fraction t.

    * ``taper``: the upper part narrows smoothly (smoothstep over ``lo..hi``)
      by this fraction, so head and trunk read as one soft blob.
    * ``fullness`` < 1 fills out the lower half (squatter, rounder base);
      1 keeps the plain sphere belly.
    """
    t = min(max(t, 0.0), 1.0)
    factor = 1.0 - taper * smoothstep(lo, hi, t)
    if fullness != 1.0 and t < 0.5:
        latitude = 1.0 - (2.0 * t - 1.0) ** 2
        if latitude > 1e-9:
            factor *= latitude ** (0.5 * (fullness - 1.0))
    return factor


def _profile(t: float, taper: float, lo: float, hi: float, fullness: float) -> float:
    latitude = 1.0 - (2.0 * t - 1.0) ** 2
    if latitude <= 0.0:
        return 0.0
    return math.sqrt(latitude) * _radial_factor(t, taper, lo, hi, fullness)


@functools.lru_cache(maxsize=None)
def _profile_peak(taper: float, lo: float, hi: float, fullness: float) -> float:
    return max(_profile(i / 2000.0, taper, lo, hi, fullness) for i in range(2001))


def body_profile(t: float, config: dict) -> float:
    """Body XY radius at height fraction t, in units of SPHERE_RADIUS (unnormalised)."""
    return _profile(t, *_profile_keys(config))


def body_xy_scale(config: dict) -> float:
    """XY factor so the widest point of the body is exactly ``body_width / 2``."""
    return (config["body_width"] / 2.0) / (SPHERE_RADIUS * _profile_peak(*_profile_keys(config)))


def body_radius_at(z: float, config: dict) -> float:
    """XY radius of the body surface at world height ``z`` (0 outside the body)."""
    t = (z - config["body_bottom_z"]) / config["body_height"]
    if t <= 0.0 or t >= 1.0:
        return 0.0
    return SPHERE_RADIUS * body_profile(t, config) * body_xy_scale(config)


def body_slope_at(z: float, config: dict, h: float = 1e-3) -> float:
    """d(radius)/dz of the body surface at height ``z``."""
    return (body_radius_at(z + h, config) - body_radius_at(z - h, config)) / (2.0 * h)


def height_at(config: dict, ratio: float) -> float:
    return config["body_bottom_z"] + config["body_height"] * ratio


def derive_base_dimensions(config: dict) -> dict:
    """Body, feet, hands and eyes, derived from the actual body surface."""
    dims: dict = {}
    body_bottom = config["body_bottom_z"]
    dims["body_bottom_z"] = body_bottom
    dims["body_top_z"] = body_bottom + config["body_height"]
    dims["body_center_z"] = body_bottom + config["body_height"] / 2.0
    dims["body_max_radius"] = config["body_width"] / 2.0

    # Feet: both soles exactly on the ground plane.
    dims["foot_center_z"] = config["foot_height"] / 2.0
    dims["foot_x"] = config["foot_spacing"] / 2.0
    dims["foot_y"] = FRONT_SIGN * config["foot_forward"]

    # Hands: seated against the flank, partly embedded.
    hand_z = height_at(config, config["hand_height_ratio"])
    hand_r = body_radius_at(hand_z, config)
    hand_ring = hand_r + config["hand_diameter"] * (0.5 - config["hand_embed"])
    dims["hand_z"] = hand_z
    dims["hand_y"] = FRONT_SIGN * config["hand_forward"]
    dims["hand_x"] = math.sqrt(max(hand_ring ** 2 - config["hand_forward"] ** 2, 0.0))
    dims["body_radius_at_hands"] = hand_r

    # Eyes: on the surface of revolution at their height, pushed outwards.
    eye_z = height_at(config, config["eye_height_ratio"])
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
    return dims


def preview_camera(config: dict, lo, hi) -> dict:
    """Orthographic preview camera framing the measured figure bounds from the front."""
    pitch = math.radians(config["preview_pitch_deg"])
    width, depth, height = (hi[i] - lo[i] for i in range(3))
    target = tuple((lo[i] + hi[i]) / 2.0 for i in range(3))
    res_x, res_y = config["preview_resolution"]
    # A world-vertical edge projects onto the camera's up axis by cos(pitch),
    # a world-horizontal (depth) edge by sin(pitch).
    vertical_need = height * math.cos(pitch) + depth * math.sin(pitch)
    horizontal_need = width / (res_x / res_y)
    return {
        "target": target,
        "ortho_scale": max(vertical_need, horizontal_need) * config["preview_margin"],
    }


def orbit(target, yaw_deg: float, pitch_deg: float, distance: float) -> tuple:
    """Camera location and euler rotation looking at ``target``.

    Yaw 0 is the front camera on -Y (FRONT_SIGN); positive yaw orbits
    counter-clockwise seen from above.
    """
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    hx, hy = math.sin(yaw), FRONT_SIGN * math.cos(yaw)
    location = (
        target[0] + hx * math.cos(pitch) * distance,
        target[1] + hy * math.cos(pitch) * distance,
        target[2] + math.sin(pitch) * distance,
    )
    return location, (math.pi / 2.0 - pitch, 0.0, yaw)


# ---------------------------------------------------------------------------
# Small Blender helpers
# ---------------------------------------------------------------------------

def log(spec: dict, message: str) -> None:
    print(f"[{spec['stem']}] {message}", flush=True)


def link_only(obj, collection) -> None:
    """Make ``collection`` the only collection ``obj`` is linked into."""
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)


def shade_smooth(mesh, sharp_angle_deg=None) -> None:
    """Smooth-shade every face; optionally keep edges above an angle sharp."""
    mesh.shade_smooth()
    if sharp_angle_deg is not None:
        mesh.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))


def object_from_bmesh(name: str, bm, mesh_name=None):
    """Write ``bm`` into a new mesh + object via bpy.data (no operators)."""
    mesh = bpy.data.meshes.new(mesh_name or name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return bpy.data.objects.new(name, mesh)


def material(config: dict, key: str):
    """Flat, matte Principled BSDF material from ``config["materials"][key]``
    = (material name, sRGB colour)."""
    name, srgb = config["materials"][key]
    rgba = srgb_to_linear(srgb)
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):  # node materials are the default from 5.0 on
        mat.use_nodes = True
    mat.diffuse_color = rgba
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.85
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def clear_scene() -> None:
    """Wipe the factory-startup scene. Destructive: run only in its own process."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.collections, bpy.data.meshes, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            datablocks.remove(block)


def add_sphere(name: str, extents, location, segments, rotation=(0.0, 0.0, 0.0),
               pivot=(0.0, 0.0, 0.0), bake_rotation: bool = False):
    """UV sphere with full ``extents`` (x, y, z) baked into the mesh.

    ``pivot`` is the object origin in the sphere's own (unrotated) frame,
    relative to its centre; ``location`` is always the sphere centre. With
    ``bake_rotation`` the rotation goes into the mesh and the node keeps a
    zero rotation (cleaner for node animation and for the intake's
    transform bake).
    """
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments[0], v_segments=segments[1], radius=SPHERE_RADIUS)
    bmesh.ops.scale(bm, vec=Vector(extents), verts=bm.verts)
    bmesh.ops.translate(bm, vec=-Vector(pivot), verts=bm.verts)
    rot = Euler(rotation).to_matrix()
    if bake_rotation:
        bmesh.ops.rotate(bm, cent=Vector((0.0, 0.0, 0.0)), matrix=rot, verts=bm.verts)
    obj = object_from_bmesh(name, bm)
    obj.location = Vector(location) + rot @ Vector(pivot)
    if not bake_rotation:
        obj.rotation_euler = rotation
    shade_smooth(obj.data)
    return obj


def add_rounded_box(name: str, extents, location, bevel: float):
    """Box with full ``extents`` and bevelled edges, baked into the mesh."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(extents), verts=bm.verts)
    bmesh.ops.bevel(
        bm, geom=list(bm.verts) + list(bm.edges), offset=bevel,
        offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES',
    )
    obj = object_from_bmesh(name, bm)
    obj.location = location
    return obj


# ---------------------------------------------------------------------------
# Shared body parts
# ---------------------------------------------------------------------------

def build_body(config: dict, dims: dict):
    """Body+head blob in one mesh. ``body_pivot`` "center" or "bottom" (for
    squash/stretch and tilting about the ground contact)."""
    bm = bmesh.new()
    around, rings = config["body_segments"]
    bmesh.ops.create_uvsphere(bm, u_segments=around, v_segments=rings, radius=SPHERE_RADIUS)

    keys = _profile_keys(config)
    xy_scale = body_xy_scale(config)
    height_scale = config["body_height"] / (2.0 * SPHERE_RADIUS)
    for vert in bm.verts:
        t = (vert.co.z + SPHERE_RADIUS) / (2.0 * SPHERE_RADIUS)
        radial = _radial_factor(t, *keys) * xy_scale
        vert.co.x *= radial
        vert.co.y *= radial
        vert.co.z *= height_scale

    location_z = dims["body_center_z"]
    if config.get("body_pivot", "center") == "bottom":
        bmesh.ops.translate(bm, vec=Vector((0.0, 0.0, config["body_height"] / 2.0)), verts=bm.verts)
        location_z = dims["body_bottom_z"]
    obj = object_from_bmesh("Body", bm)
    shade_smooth(obj.data)
    obj.location = (0.0, 0.0, location_z)
    obj.data.materials.append(material(config, "body"))
    return obj


def build_feet(config: dict, dims: dict) -> list:
    mat = material(config, "feet")
    feet = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        obj = add_sphere(
            f"Foot.{side}",
            segments=config.get("foot_segments", config["part_segments"]),
            extents=(config["foot_width"], config["foot_length"], config["foot_height"]),
            location=(sign * dims["foot_x"], dims["foot_y"], dims["foot_center_z"]),
        )
        obj.data.materials.append(mat)
        feet.append(obj)
    return feet


def build_hands(config: dict, dims: dict) -> list:
    """Short rounded stubs; the lower ends splay outwards by ``hand_angle_deg``
    and swing forwards by ``hand_pitch_deg`` (optional, default 0).

    ``hand_pivot_ratio``: node origin along the stub from its centre towards
    the upper (attachment) end, as a fraction of ``hand_length`` (0.5 = end).
    """
    mat = material(config, config.get("hand_material", "body"))
    pivot = (0.0, 0.0, config.get("hand_pivot_ratio", 0.0) * config["hand_length"])
    # A positive rotation about +X moves the lower end towards +Y, so the
    # front (-Y) needs the angle times FRONT_SIGN.
    pitch = FRONT_SIGN * math.radians(config.get("hand_pitch_deg", 0.0))
    hands = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        obj = add_sphere(
            f"Hand.{side}",
            segments=config.get("hand_segments", config["part_segments"]),
            extents=(config["hand_diameter"], config["hand_diameter"], config["hand_length"]),
            location=(sign * dims["hand_x"], dims["hand_y"], dims["hand_z"]),
            # Relaxed, hanging pose. (Tilting the upper ends out read as ears
            # from the elevated preview camera.)
            rotation=(pitch, -sign * math.radians(config["hand_angle_deg"]), 0.0),
            pivot=pivot,
            bake_rotation=config.get("bake_rotations", False),
        )
        obj.data.materials.append(mat)
        hands.append(obj)
    return hands


def eye_frame(dims: dict, sign: float) -> tuple:
    """Eye centre, horizontal outward direction and the yaw (about Z) that
    turns an eye's local +Y (its depth axis) onto that direction."""
    centre = (sign * dims["eye_x"], dims["eye_y"], dims["eye_z"])
    length = math.hypot(centre[0], centre[1])
    outward = (centre[0] / length, centre[1] / length, 0.0)
    return centre, outward, math.atan2(-outward[0], outward[1])


def eye_depth_axis(config: dict, outward) -> tuple:
    """Unit depth axis of a flattened eye: outward, tilted up by ``eye_tilt_deg``."""
    tilt = math.radians(config.get("eye_tilt_deg", 0.0))
    return (outward[0] * math.cos(tilt), outward[1] * math.cos(tilt), math.sin(tilt))


def eye_surface_distance(config: dict, outward, direction) -> float:
    """Distance from the eye centre to its surface along unit ``direction``.

    The eye is an ellipsoid: ``eye_diameter`` across, and
    ``eye_diameter * eye_depth_ratio`` along its depth axis (see
    ``eye_depth_axis``). A flatter, button-like eye protrudes less, so it
    does not peek over the head when seen from behind and above; tilting its
    face up keeps it round for the 50 degree game camera.
    """
    radius = config["eye_diameter"] / 2.0
    depth = radius * config.get("eye_depth_ratio", 1.0)
    along = sum(d * o for d, o in zip(direction, eye_depth_axis(config, outward)))
    across_sq = max(1.0 - along * along, 0.0)
    return 1.0 / math.sqrt((along / depth) ** 2 + across_sq / radius ** 2)


def build_eyes(config: dict, dims: dict) -> list:
    """Dark eyes with a small white catch-light (``eye_shine_diameter``, 0 = off).

    ``eye_depth_ratio`` < 1 flattens the eyes along the outward direction;
    they are then yawed to face outwards and tilted up by ``eye_tilt_deg``
    (baked with ``bake_rotations``).
    """
    mat = material(config, "eyes")
    diameter = config["eye_diameter"]
    depth_ratio = config.get("eye_depth_ratio", 1.0)
    parts = []
    for side, sign in (("L", 1.0), ("R", -1.0)):
        centre, _outward, yaw = eye_frame(dims, sign)
        obj = add_sphere(
            f"Eye.{side}",
            segments=config.get("eye_segments", config["part_segments"]),
            extents=(diameter, diameter * depth_ratio, diameter),
            location=centre,
            rotation=((math.radians(config.get("eye_tilt_deg", 0.0)), 0.0, yaw)
                      if depth_ratio != 1.0 else (0.0, 0.0, 0.0)),
            bake_rotation=config.get("bake_rotations", False),
        )
        obj.data.materials.append(mat)
        parts.append(obj)

    shine = config["eye_shine_diameter"]
    if shine > 0.0:
        shine_mat = material(config, "eye_shine")
        for side, sign in (("L", 1.0), ("R", -1.0)):
            centre, outward, _yaw = eye_frame(dims, sign)
            centre, outward = Vector(centre), Vector(outward)
            direction = (outward + Vector(EYE_SHINE_LIGHT)).normalized()
            if depth_ratio == 1.0:
                reach = diameter / 2.0
            else:
                reach = eye_surface_distance(config, outward, direction)
            obj = add_sphere(
                f"EyeShine.{side}",
                extents=(shine, shine, shine),
                location=centre + direction * (reach - shine * 0.2),
                segments=config.get("eye_shine_segments", (12, 6)),
            )
            obj.data.materials.append(shine_mat)
            parts.append(obj)
    return parts


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_character(config: dict, dims: dict, spec: dict):
    """Build the shared parts plus ``spec["build_parts"]`` and set up the hierarchy.

    Every part is built at its world position. ``spec["parents"]`` maps a
    part name to its parent part (default: the root empty); children keep
    their world placement. Parents must carry no rotation, so a child's
    local location is simply its world location minus the parent's.
    """
    coll = bpy.data.collections.new(spec["collection"])
    bpy.context.scene.collection.children.link(coll)
    root = bpy.data.objects.new(spec["root"], None)
    root.empty_display_size = 0.1
    coll.objects.link(root)

    parts = [build_body(config, dims)]
    parts += build_feet(config, dims)
    parts += build_hands(config, dims)
    parts += build_eyes(config, dims)
    parts += spec["build_parts"](config, dims)

    by_name = {obj.name: obj for obj in parts}
    world = {obj.name: obj.location.copy() for obj in parts}
    parents = spec.get("parents", {})
    for obj in parts:
        link_only(obj, coll)
        parent_name = parents.get(obj.name)
        if parent_name is None:
            obj.parent = root
            continue
        parent = by_name[parent_name]
        if any(abs(a) > 1e-9 for a in parent.rotation_euler):
            raise ValueError(f"parent {parent_name} of {obj.name} must not be rotated")
        obj.parent = parent
        obj.location = world[obj.name] - world[parent_name]
    bpy.context.view_layer.update()
    return coll, root


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def measure(collection) -> tuple:
    """World-space vertex bounds (lo, hi) and triangle count of all meshes."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    tris = 0
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        tris += len(mesh.loop_triangles)
        for vert in mesh.vertices:
            co = evaluated.matrix_world @ vert.co
            for i in range(3):
                lo[i] = min(lo[i], co[i])
                hi[i] = max(hi[i], co[i])
        evaluated.to_mesh_clear()
    return tuple(lo), tuple(hi), tris


def part_intersections(collection, pairs, spec: dict) -> int:
    """Print every pair of parts whose meshes intersect (BVH overlap); return the count."""
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
    for a, b in pairs:
        if a not in trees or b not in trees:
            raise ValueError(f"separate_parts names an unknown part: {a} / {b}")
        overlap = trees[a].overlap(trees[b])
        if overlap:
            hits += 1
            log(spec, f"WARNING intersection: {a} x {b} ({len(overlap)} face pairs)")
    log(spec, f"Part intersection check: {hits} of {len(pairs)} pairs intersect")
    return hits


def inspect_glb(path: Path, front_node: str) -> dict:
    """Read the GLB JSON: node names, scales and the front direction.

    ``front_z`` is the glTF world z of ``front_node`` (an eye): > 0 means
    the face looks towards glTF +Z.
    """
    with open(path, "rb") as handle:
        magic, _version, _length = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF":
            raise ValueError(f"{path} is not a GLB file")
        chunk_length, _chunk_type = struct.unpack("<I4s", handle.read(8))
        document = json.loads(handle.read(chunk_length).decode("utf-8"))
    nodes = document.get("nodes", [])
    parent_of = {child: i for i, node in enumerate(nodes) for child in node.get("children", [])}

    def local(node):
        t = node.get("translation", (0.0, 0.0, 0.0))
        x, y, z, w = node.get("rotation", (0.0, 0.0, 0.0, 1.0))
        s = node.get("scale", (1.0, 1.0, 1.0))
        return Matrix.LocRotScale(Vector(t), Quaternion((w, x, y, z)), Vector(s))

    def world(index):
        matrix = local(nodes[index])
        while index in parent_of:
            index = parent_of[index]
            matrix = local(nodes[index]) @ matrix
        return matrix

    names = [node.get("name", "?") for node in nodes]
    front_z = None
    if front_node in names:
        front_z = world(names.index(front_node)).translation.z
    return {
        "nodes": names,
        "scaled": [n.get("name", "?") for n in nodes if "scale" in n
                   and any(abs(v - 1.0) > 1e-6 for v in n["scale"])],
        "meshes": len(document.get("meshes", [])),
        "materials": len(document.get("materials", [])),
        "cameras": len(document.get("cameras", [])),
        "lights": len(document.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])),
        "front_z": front_z,
        "hierarchy": {names[c]: names[p] for c, p in parent_of.items()},
    }


# ---------------------------------------------------------------------------
# Export / preview / render
# ---------------------------------------------------------------------------

def export_glb(filepath: Path, collection) -> None:
    """Export only the character (geometry + materials, hierarchy kept).

    Runs before the preview setup exists, so no camera, light or ground
    can leak into the file. Converts to Y-up: the -Y face ends up on +Z.
    """
    members = set(collection.all_objects)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in members)
    # Operator by nature; needs no UI context in background mode.
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


def build_preview_setup(config: dict, spec: dict, camera_frame: dict, height: float):
    """Ground plane, soft sun and orthographic camera (local preview only)."""
    coll = bpy.data.collections.new(spec["preview_collection"])
    bpy.context.scene.collection.children.link(coll)

    ground_mesh = bpy.data.meshes.new("Preview_Ground")
    ground_mesh.from_pydata([(-2.0, -2.0, 0.0), (2.0, -2.0, 0.0), (2.0, 2.0, 0.0), (-2.0, 2.0, 0.0)],
                            [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("Preview_Ground", ground_mesh)
    ground.data.materials.append(material(config, "preview_ground"))
    link_only(ground, coll)

    camera = bpy.data.objects.new("Preview_Camera", bpy.data.cameras.new("Preview_Camera"))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = camera_frame["ortho_scale"]
    camera.location, camera.rotation_euler = orbit(
        camera_frame["target"], 0.0, config["preview_pitch_deg"], config["preview_distance"])
    link_only(camera, coll)

    sun = bpy.data.objects.new("Preview_Sun", bpy.data.lights.new("Preview_Sun", type='SUN'))
    sun.location = (1.5, FRONT_SIGN * 1.5, height + 1.5)
    sun.data.energy = 2.5
    sun.data.angle = math.radians(20.0)  # wide angle -> soft shadow edges
    link_only(sun, coll)

    bpy.context.scene.camera = camera
    return camera


def configure_render(scene, config: dict, output_path: Path) -> None:
    """Cycles on CPU (portable, no GPU assumed); set before saving the .blend."""
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


def write_figure_height_crops(scene, camera, collection, config: dict, spec: dict, preview_png: Path) -> list:
    """Crop the preview to the figure, scaled so the *figure* is each of
    ``views_figure_heights`` pixels tall."""
    import numpy as np

    x0, y0, x1, y1 = _figure_pixel_box(scene, camera, collection)
    figure_height = y1 - y0
    log(spec, f"Figure height in preview: {figure_height:.0f} px of {scene.render.resolution_y} px image height")

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
        path = preview_png.with_name(f"{spec['stem']}_fig{target}px.png")
        image.filepath_raw = str(path)
        image.file_format = 'PNG'
        image.save()
        bpy.data.images.remove(image)
        written.append(path)
    return written


def render_check_views(scene, camera, camera_frame: dict, views, config: dict, spec: dict,
                       output_dir: Path) -> list:
    """Orbit the preview camera for each ``(name, yaw_deg, pitch_deg)``; the
    .blend is already saved, so its preview setup stays unchanged."""
    scene.cycles.samples = config["views_samples"]
    written = []
    for name, yaw_deg, pitch_deg in views:
        camera.location, camera.rotation_euler = orbit(
            camera_frame["target"], yaw_deg, pitch_deg, config["preview_distance"])
        path = output_dir / f"{spec['stem']}_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# CLI / driver
# ---------------------------------------------------------------------------

def parse_args(spec: dict, argv=None) -> argparse.Namespace:
    argv = sys.argv if argv is None else argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(
        prog=f"{spec['stem']}.py",
        description=f"Generate the Spirit Village {spec['label']} (Blender-side).",
    )
    default_dir = f"build/characters/{spec['stem']}"
    parser.add_argument(
        "--output-dir", type=str, default=default_dir,
        help=f"Directory for {spec['stem']}.blend / .glb / PNGs (relative to the "
             f"working directory). Default: {default_dir}",
    )
    parser.add_argument("--render", action="store_true",
                        help="Also render the PNG preview (orthographic, 50 degree tilt).")
    parser.add_argument("--views", action="store_true",
                        help="Visual check set (implies --render): check views plus crops "
                             "at 96/48 px figure height.")
    return parser.parse_args(argv)


def run(config: dict, spec: dict) -> None:
    """Build, check, export, save and optionally render one creature.

    Exits with code 1 *after* all outputs are written if a check fails
    (intersections, ground contact, height range, triangle budget, node
    scale, front direction), so the renders stay available for review.
    """
    stem = spec["stem"]
    if bpy is None:
        sys.exit(
            f"{stem}.py must be run from inside Blender, e.g.:\n"
            f"  blender --background --factory-startup --python-exit-code 1 --python "
            f"art/generators/{stem}.py -- --output-dir build/characters/{stem}"
        )

    args = parse_args(spec)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log(spec, f"Blender {bpy.app.version_string}, API target: {BLENDER_API_TARGET}")
    log(spec, f"Output directory: {output_dir}")

    dims = spec["derive"](config)
    clear_scene()
    coll, _root = build_character(config, dims, spec)

    failures = []
    lo, hi, tris = measure(coll)
    height = hi[2] - lo[2]
    low, high = spec["height_range"]
    log(spec, f"Height (vertices) {height:.3f} m, lowest point {lo[2]:+.4f}, "
              f"footprint {hi[0] - lo[0]:.3f} x {hi[1] - lo[1]:.3f} m, range {low:.2f}-{high:.2f}")
    log(spec, f"Triangles {tris} (budget {spec['triangle_budget']})")
    if abs(lo[2]) > 1e-4:
        failures.append(f"ground contact {lo[2]:+.4f}")
    if not low <= height <= high:
        failures.append(f"height {height:.3f} outside {low}-{high}")
    if tris > spec["triangle_budget"]:
        failures.append(f"triangles {tris} > {spec['triangle_budget']}")
    if part_intersections(coll, spec["separate_parts"], spec):
        failures.append("part intersections")

    glb_path = output_dir / f"{stem}.glb"
    export_glb(glb_path, coll)
    glb = inspect_glb(glb_path, spec["front_node"])
    front = "missing" if glb["front_z"] is None else f"{glb['front_z']:+.3f}"
    log(spec, f"Exported GLB {glb_path.name}: {len(glb['nodes'])} nodes, {glb['meshes']} meshes, "
              f"{glb['materials']} materials, cameras {glb['cameras']}, lights {glb['lights']}, "
              f"scaled nodes {glb['scaled'] or 'none'}, {spec['front_node']} glTF z {front}")
    if glb["hierarchy"]:
        nested = {c: p for c, p in glb["hierarchy"].items() if p != spec["root"]}
        log(spec, f"GLB hierarchy (non-root parents): {nested or 'flat'}")
    if glb["scaled"]:
        failures.append(f"node scale on {glb['scaled']}")
    if glb["cameras"] or glb["lights"]:
        failures.append("camera/light in GLB")
    if glb["front_z"] is None or glb["front_z"] <= 0.0:
        failures.append("front is not glTF +Z")

    camera_frame = preview_camera(config, lo, hi)
    camera = build_preview_setup(config, spec, camera_frame, height)
    png_path = output_dir / f"{stem}_preview.png"
    scene = bpy.context.scene
    configure_render(scene, config, png_path)
    blend_path = output_dir / f"{stem}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    log(spec, f"Saved .blend (character + preview setup): {blend_path}")

    if args.render or args.views:
        bpy.ops.render.render(write_still=True)
        log(spec, f"Rendered preview PNG: {png_path}")
    if args.views:
        for path in write_figure_height_crops(scene, camera, coll, config, spec, png_path):
            log(spec, f"Wrote figure-height crop: {path}")
        views = spec["check_views"](config, dims)
        for path in render_check_views(scene, camera, camera_frame, views, config, spec, output_dir):
            log(spec, f"Rendered check view: {path}")

    if failures:
        log(spec, "CHECKS FAILED: " + "; ".join(failures))
        sys.exit(1)
    log(spec, "All checks passed")
