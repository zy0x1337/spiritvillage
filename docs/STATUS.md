# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git; Godot 4.6 `game/`.
- S2: `intake.py` + manifest + `art/ASSETS.md`.
- S3: `lineup.py`; **player = Garden Wight (A)**, 0.90 m.
- S5: `creature_base.py`; **forest spirit** 0.65 m, 4,648 tris.
- S4a: trees `tree_common_3`/`_5`, bush `bush_common_flowers`; leaves brightened; cottage/oven in `game/assets/buildings/`.
- S4b: `garden.tscn` (ground, 3×3 beet, buildings, trees, player + spirit); ortho width 6 m at 50°; `crop_growth.gd`/`crop_plot.gd`; `tests/test_crop_growth.gd`; `tools/capture.gd`; post-import `shared_materials.gd` (leaf cards cast no shadow).
- **S7:** `art/tools/render_icons.py` — 10 transparent 256×256 icons in `game/assets/icons/` from one 3/4 view/light, per-object framing; sheet `docs/previews/icons_sheet.png`.

**Checks:** Godot `--import` exit 0, 0 ERROR; crop-growth tests 6/6 PASS; `--quit-after 120` 0 ERROR; capture 360×800, 60.0 FPS; S7 second run byte-identical (SHA-256, 10/10).
**NOT RUN:** phone tests.

**Findings:** S7 crops (thin seedlings) cover 6–12 % of the icon, below the 15 % floor, though fully framed. S4c list (background band, clipped cottage, hard shadows, bare ground) still open.
**Next step:** S4c scene polish, S6 animations, then phone acceptance.
