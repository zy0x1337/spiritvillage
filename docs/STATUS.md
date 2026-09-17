# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git; Godot 4.6 project `game/`.
- S2: `intake.py` + manifest + `art/ASSETS.md`.
- S3: `lineup.py`; **player = Garden Wight (A)**, 0.90 m.
- S5: `creature_base.py`; **forest spirit** 0.65 m, 4,648 tris.
- S4a: trees `tree_common_3`/`_5`, bush `bush_common_flowers`; leaves brightened via `material_map`; cottage and oven in `game/assets/buildings/`.
- **S4b:** `game/scenes/garden.tscn` (16×16 ground, 3×3 beet, cottage/oven/barrel, 4 trees, 2 bushes, player + spirit); camera ortho, width 6 m, 50° down; `crop_growth.gd` (pure logic) + `crop_plot.gd`; `tests/test_crop_growth.gd`; `tools/capture.gd`; post-import `scripts/import/shared_materials.gd` splits bark/leaf meshes so leaf cards cast no shadow (trunks do), crops/props/bushes cast none.

**Checks:** Godot `--import` exit 0, 0 ERROR; crop-growth tests 6/6 PASS; `--quit-after 120` 0 ERROR; capture 360×800, avg 60.0 FPS.
**NOT RUN:** phone tests.
**Open decisions:** paid editions.
**Next step:** S6 animations; then phone acceptance.
