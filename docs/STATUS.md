# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, conventions (GLB, 1 m, +Z front, y=0), CC0 sources, buildings via own generators, budgets, sessions S0–S9.
- `art/generators/garden_wight.py` (~9.2k tris); workflow in `art/BLENDER_WORKFLOW.md`.
- S0: Quaternius packs outside Git, `SV_ASSET_SOURCE=D:\Mika\assets`.
- S1: Godot 4.6 project `game/` (portrait 360×800), `garden.tscn` with ortho camera, sun, ground.
- S2: `art/tools/intake.py` + manifest + `art/ASSETS.md`; 9 GLBs in `game/assets/` (carrot stages, tree, barrel, Mushnub, garden wight).
- S8: `art/generators/bldg_cottage.py` (7,128 tris, hinged `Door`, lantern anchor), renders `docs/previews/bldg_cottage*.png`.

**Checks:** S2 intake + `--verify` PASS (9/9), rerun byte-identical, Godot `--import` clean. S8 `--views` exit 0, 0/15 intersections, door +Z.
**NOT RUN:** cottage Godot import; phone tests.

**Findings:** tree 6,265 tris > 4,000; wight 0.90 m vs documented 0.95; Godot duplicates embedded textures as PNG; camera keeps height (S4). Cottage roof dominates, shingles read as petals (S8b).

**Open decisions:** player variant (S3, rec. A); paid editions.

**Next step:** S3 lineup (Claude), S8b cottage rework (Claude), then S9 oven.
