# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, asset conventions (GLB, 1 m, +Z front, y=0), CC0 sources, buildings via own generators, mobile budgets, sessions S0–S9.
- `art/generators/garden_wight.py` — player candidate (~9.2k tris); workflow in `art/BLENDER_WORKFLOW.md`.
- S0: Quaternius packs at `D:\Mika\assets\quaternius\`, `SV_ASSET_SOURCE=D:\Mika\assets`.
- S1: Godot 4.6 project `game/` (portrait 360×800), `garden.tscn` with ortho camera 50°, sun, 8×8 m ground.
- S8: `art/generators/bldg_cottage.py` — Wurzelheim cottage (7,128 tris), nodes incl. hinged `Door`, `Lantern`/`LanternLight`; self-checks; renders `docs/previews/bldg_cottage*.png`.

**Checks:** S1 `--import`/`--quit-after 5` clean. S8 `--views` exit 0, 0/15 intersections, ground 0, GLB door +Z; images reviewed.
**NOT RUN:** Godot import of generated GLBs; phone tests.

**Known issues:** S1 camera keeps height (fix in S4). Cottage: roof dominates at 50°, faint cap shading streaks, blocky steps (`art/README.md`).

**Open decisions:** player variant (S3, rec. A); paid pack editions.

**Next step:** S9 oven (template `bldg_cottage.py`); S2 intake; mark S8 done in PIPELINE.
