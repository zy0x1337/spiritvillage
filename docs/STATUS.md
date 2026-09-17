# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, asset conventions (GLB, 1 m, +Z front, y=0), CC0 sources, player variants, buildings via own generators (Farm Buildings rejected), mobile budgets, sessions S0–S9.
- `art/generators/garden_wight.py` — data-API generator, `--views` check (~9.2k tris); workflow and Blender MCP in `art/BLENDER_WORKFLOW.md`.
- S0: Quaternius packs outside Git at `D:\Mika\assets\quaternius\`, `SV_ASSET_SOURCE=D:\Mika\assets`.
- S1: Godot 4.6 project `game/` (Mobile, portrait 360×800); `garden.tscn` with ortho camera 50°, warm shadowed sun, environment, 8×8 m ground.

**Checks:** S1 `--import` and `--quit-after 5` without errors (`025546e`). Generator `--views` PASS at `ebf56e2`.
**NOT RUN:** MCP tools inside a Claude Code session; phone tests.

**Known issue:** camera keeps height; phones narrower than 9:20 crop the 8 m area (fix in S4).

**Open decisions:** player variant (S3, rec. A); paid pack editions.

**Next step:** S2 intake (DeepSeek) and S8 cottage generator (Claude) in parallel.
