# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git; Godot 4.6 project `game/` with `garden.tscn`.
- S2: `intake.py` + manifest + `art/ASSETS.md`; 10 GLBs in `game/assets/`.
- S8/S8b: `bldg_cottage.py` (7,128 tris).
- S3: `lineup.py`; **player = Garden Wight (A)**, 0.90 m; carrots/barrel rescaled.
- S5: shared `creature_base.py`; Garden Wight colours sRGB; **forest spirit** 0.65 m, 4,648 tris with pivots for S6.
- S9: `bldg_oven.py` (2,992 tris): dry-stone drum, arched fire opening with embers, rim grate, cauldron + soup; `SteamAnchor`/`FireLight`.

**Checks:** S9 `--views` exit 0, 0/7 intersections, lowest 0.0000, GLB without scale/cameras/lights, opening +Z. S5 0 intersections; intake `--verify` 10/10; Godot `--import`, lineup clean; renders reviewed.
**NOT RUN:** phone tests; no building in `game/assets/`.

**Findings:** player 32 px, spirit 24 px at the S1 camera (rec. ~6 m width); S9 body 0.675 m, rim 1.007 m; raised bail invisible at 50° → side rings; spirit face sits low.

**Open decisions:** camera width (S4); paid editions.

**Next step:** S4 scene and S6 animations; S7 icons.
