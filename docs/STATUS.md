# Status

**Goal:** Milestone 1 – small Godot garden scene with player, one working nature spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — art direction, asset conventions (GLB, 1 m, +Z front, y=0), CC0 provenance, player variants, spirit template, mobile budgets, session plan S0–S7.
- `art/generators/garden_wight.py` — data-API generator, `--views` check (~9.2k tris); workflow in `art/BLENDER_WORKFLOW.md`.
- Blender MCP on user PC: `mcp-for-blender` 2.0.0, local Claude Code scope, telemetry off.
- **S0 done:** Quaternius packs kept outside Git at `D:\Mika\assets\quaternius\`; `SV_ASSET_SOURCE=D:\Mika\assets`.
- **S1 done:** decision "Godot project in `game/`" implemented. Godot 4.6 project: name "Spirit Village", Mobile renderer, portrait 360×800, stretch `canvas_items`/`expand`, main scene `res://scenes/garden.tscn`. `garden.tscn`: orthographic Camera3D (50° down, size 18), warm shadow-casting DirectionalLight3D, bright warm WorldEnvironment, 8×8 m ground plane. `game/.godot/` ignored, `*.import` versioned.

**Checks:** S1 — `Godot --headless --path game --import` exit 0, no errors; `--quit-after 5` loads the main scene, exit 0. Generator `--views` (Blender 5.2.1) PASS at `ebf56e2`.

**NOT RUN:** MCP tools inside a Claude Code session; phone tests.

**Open decisions:** player variant (S3, rec. A).

**Next step:** S2 — intake (`art/tools/intake.py`, manifest, `art/ASSETS.md`) from the S0 packs into `game/assets/`.
