"""Garden Wight character generator (Spirit Village player, char_garden_wight).

A small, pear-shaped garden being with a cream overcoat, an asymmetric
leaf-green cap, dark round eyes, two short rounded hand-stubs, two small
dark-brown feet and a brown seed bag on a shoulder strap. Body, feet,
hands, eyes, checks, export and renders come from ``creature_base.py``;
this module holds the configuration and the Garden-Wight-only parts
(cap, bag, flap, strap). Conventions: see ``creature_base.py`` and
``art/README.md``; working rules: ``art/BLENDER_WORKFLOW.md``.

Run only as a separate Blender background process with factory startup
(the scene is wiped)::

    blender --background --factory-startup --python-exit-code 1 --python \\
        art/generators/garden_wight.py -- \\
        --output-dir build/characters/garden_wight [--render | --views]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creature_base as base  # noqa: E402
from creature_base import FRONT_SIGN, body_radius_at, height_at  # noqa: E402

bmesh = base.bmesh
Vector = base.Vector


# ---------------------------------------------------------------------------
# Configuration - the single place to tune the character.
# Full extents in metres (diameter/length/width/height); ratios are fractions
# of ``body_height`` from the body's lowest point. Colours are sRGB.
# ---------------------------------------------------------------------------

CONFIG = {
    # Body silhouette (see creature_base: sphere + radial profile).
    "body_width": 0.62,           # widest diameter of the finished body
    "body_height": 0.70,          # lowest to highest point of the body blob
    "body_bottom_z": 0.045,       # body's lowest point above the ground, so the feet show
    "body_taper": 0.26,           # the head end is this much narrower than the belly (pear)
    "body_taper_range": (0.30, 0.85),  # height fractions over which the taper sets in
    "body_bottom_fullness": 1.0,  # 1 = plain sphere belly
    "body_pivot": "center",
    # Feet - soles sit exactly on z = 0.
    "foot_length": 0.17,          # along Y
    "foot_width": 0.13,           # along X
    "foot_height": 0.09,          # along Z
    "foot_spacing": 0.17,         # centre-to-centre distance
    "foot_forward": 0.10,         # toes peek out under the belly in the 50 degree view
    # Hands (short rounded stubs, no fingers).
    "hand_length": 0.17,
    "hand_diameter": 0.12,
    "hand_height_ratio": 0.46,
    "hand_forward": 0.03,         # so the stubs don't read as ears from above
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
    "cap_brim_front_lift": 0.8,   # fraction of the droop removed at the front (eyes stay clear)
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
    # Mesh detail (player budget <= 10 000 triangles, art/PIPELINE.md section 7).
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
    # Materials: (name, sRGB colour), matte and texture-free. Matched to
    # mockup.png: leaf-green cap, cream coat, warm brown leather bag.
    "materials": {
        "body": ("Mat_SkinCream", (0.96, 0.91, 0.79)),
        "feet": ("Mat_FeetBrown", (0.33, 0.23, 0.16)),
        "eyes": ("Mat_EyesDark", (0.09, 0.08, 0.08)),
        "eye_shine": ("Mat_EyeShine", (0.98, 0.98, 0.95)),
        "cap": ("Mat_CapMoss", (0.44, 0.63, 0.25)),
        "bag": ("Mat_BagOchre", (0.78, 0.56, 0.29)),
        "strap": ("Mat_StrapOchreDark", (0.58, 0.39, 0.20)),
        "preview_ground": ("Mat_PreviewGround", (0.77, 0.73, 0.67)),
    },
}

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


# ---------------------------------------------------------------------------
# Pure geometry - no bpy.
# ---------------------------------------------------------------------------

def derive_dimensions(config: dict) -> dict:
    """Shared placements plus cap, bag and strap anchors from the body surface."""
    dims = base.derive_base_dimensions(config)

    # Cap: origin at its base so the lean rotates around the brim.
    cap_base_z = height_at(config, config["cap_base_height_ratio"])
    dims["cap_base_z"] = cap_base_z
    dims["cap_tip_z"] = cap_base_z + config["cap_height"]
    dims["body_radius_at_cap"] = body_radius_at(cap_base_z, config)

    # Bag: hangs off the flank opposite the cap's lean.
    bag_sign = -1.0 if config["cap_lean_deg"] >= 0.0 else 1.0
    bag_x_size, bag_y_size, bag_z_size = config["bag_size"]
    bag_z = height_at(config, config["bag_height_ratio"])
    bag_r = body_radius_at(bag_z, config)
    dims["bag_sign"] = bag_sign
    dims["bag_center"] = (
        bag_sign * (bag_r + bag_x_size * (0.5 - config["bag_embed"])),
        FRONT_SIGN * bag_y_size * 0.25,
        bag_z,
    )
    dims["bag_top_z"] = bag_z + bag_z_size / 2.0
    dims["body_radius_at_bag"] = bag_r

    # Strap anchors: front and back of the bag's top, inset from the faces.
    bag_x, bag_y, _bag_z = dims["bag_center"]
    inset = bag_y_size * config["strap_bag_inset"]
    front_y = bag_y + FRONT_SIGN * (bag_y_size / 2.0 - inset)
    back_y = bag_y - FRONT_SIGN * (bag_y_size / 2.0 - inset)
    anchor_x = bag_x - bag_sign * bag_x_size * 0.25   # towards the body
    dims["strap_anchor_front"] = (anchor_x, front_y, dims["bag_top_z"])
    dims["strap_anchor_back"] = (anchor_x, back_y, dims["bag_top_z"])
    return dims


def _catmull_rom(p0, p1, p2, p3, t: float) -> tuple:
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * (2.0 * b + (c - a) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
               + (3.0 * b - a - 3.0 * c + d) * t3)
        for a, b, c, d in zip(p0, p1, p2, p3)
    )


def strap_path(config: dict, dims: dict, samples_per_span: int = 10) -> list:
    """Inner centre line of the strap loop, with the outward surface normal.

    Waypoints are ``(angle, z, extra)``: ``angle`` around the body from the
    front towards the bag side, ``z`` the height, ``extra`` the distance
    outside the body surface (plus ``strap_lift``). The loop runs bag front
    -> front flank -> over the shoulder at 90 deg -> back flank -> bag back;
    both ends continue ``strap_bury`` down into the bag. ``extra`` is clamped
    to >= 0, so no sample can lie inside the body.

    Returns ``(x, y, z, nx, ny, nz)`` tuples.
    """
    bag_sign = dims["bag_sign"]
    lift = config["strap_lift"]

    def to_keys(point):
        x, y, z = point
        angle = math.atan2(bag_sign * x, FRONT_SIGN * y)
        return (angle, z, math.hypot(x, y) - body_radius_at(z, config) - lift)

    def surface(ratio_key, angle_key):
        return (math.radians(config[angle_key]), height_at(config, config[ratio_key]), 0.0)

    bury = config["strap_bury"]
    front = dims["strap_anchor_front"]
    back = dims["strap_anchor_back"]
    mid = surface("strap_mid_ratio", "strap_mid_angle_deg")
    upper = surface("strap_upper_ratio", "strap_upper_angle_deg")
    crest = (math.pi / 2.0, height_at(config, config["strap_shoulder_ratio"]), 0.0)
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
            slope = base.body_slope_at(z, config)
            norm = math.sqrt(1.0 + slope * slope)
            points.append((
                dir_x * radius, dir_y * radius, z,
                dir_x / norm, dir_y / norm, -slope / norm,
            ))
    return points


# ---------------------------------------------------------------------------
# Garden-Wight-only parts
# ---------------------------------------------------------------------------

def build_cap(config: dict, dims: dict):
    """Asymmetric leaf-green cap with a drooping tip.

    A cone swept along a curved spine: straight up to ``cap_bend_start``,
    then curling by ``cap_bend_deg`` towards +X (the lean side). The mesh
    origin sits at the brim centre, so ``cap_lean_deg`` tilts the cap around
    its base. (A Simple Deform bend modifier bent the cone across its width
    and left a flat sail, hence the explicit geometry.)
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
    previous = ring_verts[0]
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

    obj = base.object_from_bmesh("Cap", bm)
    base.shade_smooth(obj.data, config["smooth_angle_deg"])  # keeps the brim edge crisp
    obj.location = (0.0, 0.0, dims["cap_base_z"])
    obj.rotation_euler = (0.0, math.radians(config["cap_lean_deg"]), 0.0)
    obj.data.materials.append(base.material(config, "cap"))
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
        taper = base.smoothstep(dims["bag_top_z"], taper_top, z)
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

    obj = base.object_from_bmesh("Strap", bm)
    base.shade_smooth(obj.data, config["smooth_angle_deg"])  # smooth along, crisp band edges
    obj.data.materials.append(base.material(config, "strap"))
    return obj


def build_bag(config: dict, dims: dict) -> list:
    bag = base.add_rounded_box("Bag", config["bag_size"], dims["bag_center"], config["bag_bevel"])
    base.shade_smooth(bag.data, config["smooth_angle_deg"])
    bag.data.materials.append(base.material(config, "bag"))

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
    flap = base.object_from_bmesh("BagFlap", bm)
    flap.location = (bag_x, bag_y, bag_z)
    base.shade_smooth(flap.data, config["smooth_angle_deg"])
    flap.data.materials.append(base.material(config, "strap"))
    return [bag, flap, build_strap(config, dims)]


def build_parts(config: dict, dims: dict) -> list:
    return [build_cap(config, dims)] + build_bag(config, dims)


def check_views(config: dict, dims: dict) -> tuple:
    side_yaw = 90.0 if dims["bag_sign"] > 0 else -90.0
    return (
        ("back", 180.0, config["preview_pitch_deg"]),
        ("side_bag", side_yaw, config["views_side_pitch_deg"]),
    )


SPEC = {
    "stem": "garden_wight",
    "label": "Garden Wight",
    "root": "GardenWight_Root",
    "collection": "GardenWight_Character",
    "preview_collection": "GardenWight_PreviewSetup",
    "derive": derive_dimensions,
    "build_parts": build_parts,
    "parents": {},                 # flat: every part directly under the root
    "separate_parts": SEPARATE_PARTS,
    "check_views": check_views,
    "front_node": "Eye.L",
    "triangle_budget": 10000,      # player, art/PIPELINE.md section 7
    "height_range": (0.89, 0.91),  # player height 0.90 m (section 2 / 4b)
}


if __name__ == "__main__":
    base.run(CONFIG, SPEC)
