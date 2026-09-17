# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, conventions (GLB, 1 m, +Z front, y=0), CC0 provenance, buildings via own generators, budgets, sessions S0–S9.
- `art/generators/garden_wight.py` (~9.2k tris); workflow and Blender MCP in `art/BLENDER_WORKFLOW.md`.
- S0: Quaternius packs outside Git (`D:\Mika\assets`), `SV_ASSET_SOURCE` set.
- S1: Godot 4.6 project `game/` (Mobile, portrait 360×800); `garden.tscn` with ortho camera 50°, warm sun, 8×8 m ground.
- S2: `art/tools/intake.py`, `art/intake_manifest.json`, `art/ASSETS.md`. Nine assets in `game/assets/` (5 carrot stages, tree, barrel, mushroom, garden wight); normal/ORM removed, metallic 0, roughness 0.9, textures ≤1024 px, no node scale, ground y=0. Godot `--import` clean, `*.import` and extracted PNGs committed.

**Checks:** S2 intake exit 0; `--verify` PASS for all 9 (min_y 0.000, centre 0, no node scale, Mushnub 9/9 animations); second run byte-identical. S1 `--import`/`--quit-after 5` clean (`025546e`).

**Findings:** `tree_common_1` 6265 tris > 4000 budget; `char_garden_wight` 9190 tris (~0.90 m); `prop_barrel` GLB 1.5 MB (two 1024 base-colour textures).

**NOT RUN:** phone tests; MCP in a Claude Code session.

**Open decisions:** player variant (S3, rec. A).

**Next step:** S3 lineup and player decision (Claude).
