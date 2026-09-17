# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, conventions, CC0 sources, buildings via generators, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git (`SV_ASSET_SOURCE`); Godot 4.6 project `game/` with `garden.tscn`.
- S2: `art/tools/intake.py` + manifest + `art/ASSETS.md`; 10 GLBs in `game/assets/`.
- S8/S8b: `art/generators/bldg_cottage.py` (7,128 tris).
- S3: `art/tools/lineup.py`; **player = Garden Wight (A)**, 0.90 m; carrots/barrel rescaled.
- S5: `art/generators/creature_base.py` shared body; Garden Wight colours sRGB (leaf green, cream, brown; geometry unchanged); **forest spirit** `char_forest_spirit` 0.65 m, 4,648 tris, node hierarchy with pivots for S6.

**Checks:** S5 both generators `--views` exit 0, 0 intersections, budgets kept; intake `--verify` 10/10 PASS; Godot `--import` exit 0 without errors; lineup exit 0. All renders reviewed.
**NOT RUN:** phone tests; cottage not yet in `game/assets/`.

**Findings:** at S1 camera the player is 32 logical px, spirit 24 px (rec. ~6 m visible width); tree narrow, dark, 6,265 tris; forest spirit face sits low from 50°.

**Open decisions:** camera width (S4); paid editions.

**Next step:** S9 oven (DeepSeek); then S4 scene and S6 animations.
