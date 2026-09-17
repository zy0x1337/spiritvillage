# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit, a growing bed, on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios, budgets, sessions S0–S9b.
- S0–S2: packs outside Git; Godot 4.6 `game/`; `intake.py` + manifest + `art/ASSETS.md`, 10 GLBs in `game/assets/`.
- S3/S5: `lineup.py`; **player = Garden Wight (A)**, 0.90 m; shared `creature_base.py` (sRGB), **forest spirit** 0.65 m / 4,648 tris, pivots for S6.
- S8/S8b: `bldg_cottage.py`.
- S9/S9b: `bldg_oven.py` (3,692 tris): dry-stone drum, arched fire opening with glowing bed and flame tongues, narrow stone rim with collar and grate, cauldron + soup; `SteamAnchor`/`FireLight`.

**Checks:** S9b `--views` exit 0, 0/7 intersections, lowest 0.0000, GLB clean (no scale/cameras/lights), opening +Z; glow visible in `game1x/3x`. S5 0 intersections; intake `--verify` 10/10; Godot `--import`, lineup clean; renders reviewed.
**NOT RUN:** phone tests; buildings not in `game/assets/`.

**Findings:** S9b body 0.687 m, rim 1.017 m; rim collar plus dark plug close the top view onto the glow; player 32 px, spirit 24 px at the S1 camera (rec. ~6 m); spirit face low.

**Open decisions:** camera width (S4b); paid editions.

**Next step:** S4a asset intake, then S4b scene and S6 animations.
