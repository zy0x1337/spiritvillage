# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction ("enchanted miniature garden"), asset conventions (GLB, 1 m, +Z front, y=0), CC0 sources and provenance rules, player variants A/B/C, spirit template, skeleton-free animation, automated path into Godot 4.6, mobile budgets, session plan S0–S7 (Claude / DeepSeek).
- `art/generators/garden_wight.py` — data-API generator, `--views` check renders, intersection check (~9.2k tris).
- `art/BLENDER_WORKFLOW.md` — generator workflow; Blender MCP setup and safety rules.
- Blender MCP on user PC: `mcp-for-blender` 2.0.0, local Claude Code scope, telemetry off, addon session-only via `art/tools/blender_mcp_session.py`.

**Checks:** MCP end-to-end on user PC — PASS (scene info, code execution, consent false; port closed and no prefs entry after exit). Generator `--views` (Blender 5.2.1) — PASS at `ebf56e2`.
**NOT RUN:** MCP tools inside a Claude Code session (need a new session); Godot import; phone tests.

**Open decisions:** player variant (S3, rec. A); raw packs outside Git (rec. yes); Godot project in `game/` (rec. yes).

**Next step:** S0 (user downloads packs) and S1 (Godot scaffold, DeepSeek) in parallel.
