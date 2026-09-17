# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git; Godot 4.6 project `game/` with `garden.tscn`.
- S2: `intake.py` + manifest + `art/ASSETS.md`.
- S8/S8b/S9/S9b: `bldg_cottage` (7,128 tris) and `bldg_oven` (3,692 tris) via Intake in `game/assets/buildings/`.
- S3: `lineup.py`; **player = Garden Wight (A)**, 0.90 m.
- S5: shared `creature_base.py`; **forest spirit** 0.65 m, 4,648 tris.
- S4a: **trees `tree_common_3` (3,505) and `tree_common_5` (3,182), bush `bush_common_flowers` (1,368)** in `game/assets/nature/`. Leaves brightened via `material_map` (light sage). Twisted trees (9.1k–10.1k) and common 1/2/4 (>4,000 or darker) removed; `tree_common_1` deleted.

**Checks:** S4a Intake exit 0, `--verify` 14/14 PASS; lineup `--set trees` exit 0 (`docs/previews/lineup_trees_1x.png`, `_3x.png`); Godot `--import` exit 0, no ERROR, no extracted PNGs (`embedded_image_handling=2`).
**NOT RUN:** phone tests.

**Findings:** leaf base texture is a dark green (sRGB ≈ 88,123,0) plus leaf-card self-shadowing; the Intake override replaces its RGB with a white+alpha texture, so the palette colour shows unmultiplied.
**Next step:** S4b garden scene (camera width, paths, bed, buildings).
