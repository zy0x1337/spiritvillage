# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, conventions, CC0 sources, buildings via generators, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git (`SV_ASSET_SOURCE`); Godot 4.6 project `game/` with `garden.tscn`.
- S2: `art/tools/intake.py` + manifest + `art/ASSETS.md`; 9 GLBs in `game/assets/`.
- S8/S8b: `art/generators/bldg_cottage.py` (7,128 tris; taller walls, tile-like shingles).
- S3: `art/tools/lineup.py`; **player = Garden Wight (A)**, 0.90 m; carrots rescaled (ripe 0.55 m), barrel 0.55 m.

**Checks:** S8b `--views` exit 0, 0/15 intersections. S3 intake + `--verify` 9/9 PASS, lineup exit 0, Godot `--import` exit 0 without errors. All renders reviewed.
**NOT RUN:** phone tests; cottage not yet in `game/assets/`.

**Findings:** at S1 camera the player is 32 logical px (rec. ~6 m visible width); tree narrow, dark, 6,265 tris; Godot duplicates embedded textures as PNG; Garden Wight colours still linear (pale).

**Open decisions:** camera width (S4); paid editions.

**Next step:** S9 oven (DeepSeek) and S5 spirit base (Claude); then S4 scene.
