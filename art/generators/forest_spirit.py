"""Forest spirit generator (Spirit Village helper, char_forest_spirit).

A squat, moss-green garden being with a two-leaf sprout on its head, small
dark eyes, stubby hands and dark-brown feet (reference: the forest spirit
on the left of ``mockup.png``). Body, feet, hands, eyes, checks, export and
renders come from ``creature_base.py``; this module holds the configuration
and the sprout (``Sprout`` stem, ``Leaf.L``/``Leaf.R``).

Animation without a skeleton (art/PIPELINE.md sections 4 and 5: short
steps, curious tilting): the node hierarchy and pivots are set up for
transform animation in Godot.

* ``ForestSpirit_Root`` -> ``Foot.L``/``Foot.R`` (pivot at the foot centre)
  and ``Body`` (pivot at the body's lowest point: tilt and squash/stretch
  about the ground contact).
* ``Body`` -> ``Eye.*`` (-> ``EyeShine.*``), ``Hand.*`` (pivot near the
  attachment on the flank, for swinging) and ``Sprout`` (pivot at the stem
  base on the head).
* ``Sprout`` -> ``Leaf.L``/``Leaf.R`` (pivot at the stem tip, for flapping).

All node rotations are zero (baked into the meshes), so the intake's
transform bake keeps every pivot.

Run only as a separate Blender background process with factory startup
(the scene is wiped)::

    blender --background --factory-startup --python-exit-code 1 --python \\
        art/generators/forest_spirit.py -- \\
        --output-dir build/characters/forest_spirit [--render | --views]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creature_base as base  # noqa: E402
from creature_base import FRONT_SIGN  # noqa: E402

bmesh = base.bmesh
Vector = base.Vector


# ---------------------------------------------------------------------------
# Configuration. Full extents in metres; ratios are fractions of
# ``body_height`` from the body's lowest point. Colours are sRGB.
# ---------------------------------------------------------------------------

CONFIG = {
    # Body silhouette: an egg that is fuller at the base than at the head.
    "body_width": 0.42,
    "body_height": 0.46,
    "body_bottom_z": 0.03,
    "body_taper": 0.08,
    "body_taper_range": (0.35, 0.95),
    "body_bottom_fullness": 0.75,  # < 1 fills out the lower half (squat)
    "body_pivot": "bottom",
    # Feet - soles on z = 0, mostly hidden under the belly.
    "foot_length": 0.13,
    "foot_width": 0.11,
    "foot_height": 0.07,
    "foot_spacing": 0.16,
    "foot_forward": 0.10,
    # Hands (stubs).
    "hand_length": 0.115,
    "hand_diameter": 0.095,
    "hand_height_ratio": 0.34,
    "hand_forward": 0.15,
    "hand_embed": 0.40,
    "hand_angle_deg": 5.0,
    "hand_pitch_deg": 80.0,        # lower ends reach forwards (carrying pose, no ear look)
    "hand_pivot_ratio": 0.35,      # node origin near the upper, embedded end
    "bake_rotations": True,
    # Eyes (small).
    "eye_diameter": 0.054,
    "eye_spacing": 0.12,
    "eye_height_ratio": 0.58,     # higher eyes peek over the head in the 50 degree back view
    "eye_protrusion": 0.08,
    "eye_depth_ratio": 0.45,       # flat, button-like eyes (see eye_surface_distance)
    "eye_tilt_deg": 25.0,          # eye face turned up towards the game camera
    "eye_shine_diameter": 0.016,
    # Sprout: stem grows from the top of the head, two leaves spread in a V.
    "stem_height": 0.09,           # from the stem base (inside the head) to the tip
    "stem_bury": 0.025,            # stem base below the top of the body
    "stem_base_diameter": 0.04,
    "stem_tip_diameter": 0.026,
    "leaf_length": 0.15,
    "leaf_width": 0.12,
    "leaf_thickness": 0.014,
    "leaf_angle_deg": 55.0,        # from vertical, outwards to each side
    "leaf_face_front_deg": 12.0,   # turns the blade's upper face towards the front
    "leaf_curl": 0.20,             # length-wise upward curl (fraction of leaf_length)
    "leaf_cup": 0.20,              # edges raised (fraction of the local half width)
    "leaf_base_offset": 0.007,     # sideways gap between the two leaf bases
    "leaf_base_drop": 0.012,       # leaf bases start this far below the stem tip (no visible gap)
    # Mesh detail (helper budget <= 6 000 triangles).
    "body_segments": (40, 24),
    "part_segments": (20, 10),     # feet, hands
    "eye_segments": (16, 8),
    "eye_shine_segments": (10, 5),
    "stem_segments": (12, 5),      # around, along
    "leaf_segments": (14, 12),     # around the blade cross-section, along the length
    # Preview only.
    "preview_pitch_deg": 50.0,
    "preview_distance": 3.0,
    "preview_margin": 1.25,
    "preview_resolution": (768, 1024),
    "views_samples": 32,
    "views_side_pitch_deg": 20.0,
    "views_figure_heights": (96, 48),
    # Materials (name, sRGB colour); matched to mockup.png.
    "materials": {
        "body": ("Mat_MossBody", (0.58, 0.72, 0.29)),
        "feet": ("Mat_FeetBrown", (0.30, 0.21, 0.15)),
        "eyes": ("Mat_EyesDark", (0.09, 0.08, 0.08)),
        "eye_shine": ("Mat_EyeShine", (0.98, 0.98, 0.95)),
        "stem": ("Mat_StemGreen", (0.47, 0.64, 0.23)),
        "leaf": ("Mat_LeafGreen", (0.62, 0.80, 0.33)),
        "preview_ground": ("Mat_PreviewGround", (0.77, 0.73, 0.67)),
    },
}

SEPARATE_PARTS = (
    ("Leaf.L", "Leaf.R"), ("Leaf.L", "Body"), ("Leaf.R", "Body"),
    ("Hand.L", "Foot.L"), ("Hand.R", "Foot.R"), ("Hand.L", "Eye.L"), ("Hand.R", "Eye.R"),
    ("Foot.L", "Foot.R"), ("Sprout", "Eye.L"), ("Sprout", "Eye.R"),
)

PARENTS = {
    "Eye.L": "Body", "Eye.R": "Body",
    "EyeShine.L": "Eye.L", "EyeShine.R": "Eye.R",
    "Hand.L": "Body", "Hand.R": "Body",
    "Sprout": "Body",
    "Leaf.L": "Sprout", "Leaf.R": "Sprout",
}


# ---------------------------------------------------------------------------
# Pure geometry - no bpy.
# ---------------------------------------------------------------------------

def _add(*vectors):
    return tuple(sum(c) for c in zip(*vectors))


def _mul(v, s):
    return tuple(c * s for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normalized(v):
    length = math.sqrt(sum(c * c for c in v))
    return tuple(c / length for c in v)


def derive_dimensions(config: dict) -> dict:
    dims = base.derive_base_dimensions(config)
    dims["stem_base_z"] = dims["body_top_z"] - config["stem_bury"]
    dims["stem_tip_z"] = dims["stem_base_z"] + config["stem_height"]
    return dims


def leaf_frame(config: dict, sign: float) -> tuple:
    """Unit axes of one leaf: ``along`` (base to tip), ``across`` the blade and
    ``up`` (normal of the blade's upper face). ``sign`` +1 = Leaf.L (+X)."""
    theta = math.radians(config["leaf_angle_deg"])
    along = (sign * math.sin(theta), 0.0, math.cos(theta))
    up = _mul(_cross(along, (0.0, 1.0, 0.0)), sign)          # up and inwards
    phi = math.radians(config["leaf_face_front_deg"])
    up = _normalized(_add(_mul(up, math.cos(phi)), (0.0, FRONT_SIGN * math.sin(phi), 0.0)))
    across = _normalized(_cross(up, along))
    return along, across, up


def leaf_rings(config: dict, sign: float) -> tuple:
    """Leaf surface in node-local coordinates (origin at the stem tip).

    Returns ``(base_pole, rings, tip_pole)``; each ring runs once around the
    blade's lens-shaped cross-section. The blade is pointed at both ends,
    widest a little below the middle, curls upwards along its length and is
    cupped across (edges raised).
    """
    along, across, up = leaf_frame(config, sign)
    around, steps = config["leaf_segments"]
    length, half_width = config["leaf_length"], config["leaf_width"] / 2.0
    start = (sign * config["leaf_base_offset"], 0.0, -config["leaf_base_drop"])

    def centre(u):
        return _add(start, _mul(along, length * u), _mul(up, config["leaf_curl"] * length * u * u))

    rings = []
    for i in range(1, steps):
        u = i / steps
        width = half_width * math.sin(math.pi * u ** 0.7)
        thick = 0.5 * config["leaf_thickness"] * math.sin(math.pi * u) ** 0.5
        ring = []
        for j in range(around):
            angle = 2.0 * math.pi * j / around
            v, w = math.cos(angle), math.sin(angle)
            lift = config["leaf_cup"] * width * v * v + thick * w
            ring.append(_add(centre(u), _mul(across, width * v), _mul(up, lift)))
        rings.append(ring)
    return centre(0.0), rings, centre(1.0)


# ---------------------------------------------------------------------------
# Forest-spirit-only parts
# ---------------------------------------------------------------------------

def _mesh_from_rings(name: str, base_pole, rings, tip_pole):
    """Closed mesh: pole fan, quad bands between rings, pole fan."""
    bm = bmesh.new()
    first = bm.verts.new(base_pole)
    ring_verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    last = bm.verts.new(tip_pole)
    count = len(rings[0])
    for j in range(count):
        k = (j + 1) % count
        bm.faces.new((first, ring_verts[0][k], ring_verts[0][j]))
        bm.faces.new((last, ring_verts[-1][j], ring_verts[-1][k]))
    for lower, upper in zip(ring_verts[:-1], ring_verts[1:]):
        for j in range(count):
            k = (j + 1) % count
            bm.faces.new((lower[j], lower[k], upper[k], upper[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return base.object_from_bmesh(name, bm)


def build_sprout(config: dict, dims: dict) -> list:
    around, steps = config["stem_segments"]
    height = config["stem_height"]
    r0, r1 = config["stem_base_diameter"] / 2.0, config["stem_tip_diameter"] / 2.0
    rings = []
    for i in range(steps + 1):
        s = i / steps
        radius = r0 + (r1 - r0) * s
        z = height * s
        rings.append([(radius * math.cos(2.0 * math.pi * j / around),
                       radius * math.sin(2.0 * math.pi * j / around), z) for j in range(around)])
    stem = _mesh_from_rings("Sprout", (0.0, 0.0, -r0), rings, (0.0, 0.0, height + r1))
    base.shade_smooth(stem.data)
    stem.location = (0.0, 0.0, dims["stem_base_z"])
    stem.data.materials.append(base.material(config, "stem"))

    parts = [stem]
    leaf_mat = base.material(config, "leaf")
    for side, sign in (("L", 1.0), ("R", -1.0)):
        leaf = _mesh_from_rings(f"Leaf.{side}", *leaf_rings(config, sign))
        base.shade_smooth(leaf.data)
        leaf.location = (0.0, 0.0, dims["stem_tip_z"])
        leaf.data.materials.append(leaf_mat)
        parts.append(leaf)
    return parts


def check_views(config: dict, dims: dict) -> tuple:
    return (
        ("back", 180.0, config["preview_pitch_deg"]),
        ("side", 90.0, config["views_side_pitch_deg"]),
    )


SPEC = {
    "stem": "forest_spirit",
    "label": "Forest Spirit",
    "root": "ForestSpirit_Root",
    "collection": "ForestSpirit_Character",
    "preview_collection": "ForestSpirit_PreviewSetup",
    "derive": derive_dimensions,
    "build_parts": build_sprout,
    "parents": PARENTS,
    "separate_parts": SEPARATE_PARTS,
    "check_views": check_views,
    "front_node": "Eye.L",
    "triangle_budget": 6000,       # helper/spirit, art/PIPELINE.md section 7
    "height_range": (0.60, 0.70),  # helper smaller than the 0.90 m player
}


if __name__ == "__main__":
    base.run(CONFIG, SPEC)
