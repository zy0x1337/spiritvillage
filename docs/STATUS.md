# Status

**Goal:** First static player character ("Garden Wight") as a reproducible Blender-Python generator. No Godot project, gameplay, rigging or animation yet.

**Implemented:**
- `art/generators/garden_wight.py` — all geometry via `bpy.data`/`bmesh` (operators only for export, save, render). Shoulder-strap loop, bag with flap, eye catch-lights, drooping cap brim, ~9.2k triangles. `--views` renders back/side views and 96/48 px figure-height crops; every run checks part intersections.
- `art/BLENDER_WORKFLOW.md` — binding generator workflow (data API, visual feedback loop, MCP/BlenderProc not set up).
- `art/README.md` — design, usage, executed vs. pending checks, findings. `docs/previews/` — real renders.

**Checks (Blender 5.2.1 LTS, user PC):** `--views` run — PASS (exit 0, 0/15 intersections). All renders viewed — PASS. GLB JSON — PASS: 14 nodes, 7 materials, no preview objects, no node scale, face +Z. Repeat export: identical except triangle order in sphere meshes.
**NOT RUN:** Godot import; other Blender versions.

**Open findings:** strap weak at 48 px figure height; hands slightly ear-like from 50°; strap kink above bag.

**Next step:** Godot import test; optionally set up Blender MCP for interactive tuning.
