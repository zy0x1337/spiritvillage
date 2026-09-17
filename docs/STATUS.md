# Status

**Goal:** First static player character ("Garden Wight") as a reproducible Blender-Python generator. No Godot project, gameplay or animation yet.

**Implemented:**
- `art/generators/garden_wight.py` — standalone Blender script. Character faces -Y (Blender front view / Godot -Z); all CONFIG values are full extents; `derive_dimensions()` places every part from the actual body surface radius; soles on z=0; orthographic camera computed from the figure's size at 50° below horizontal; render settings applied before saving; GLB export runs before the preview setup exists, so it holds the figure only.
- `art/README.md` — conventions, design, usage, camera/render rationale, open visual review points.

**Checks (no Blender here):** `py_compile` and argument/path logic — PASS. 29 numeric assertions on the script's geometry math — PASS: max diameter equals `body_width`, soles at z=0, box extents unhalved, eyes on the surface and clear of the cap brim, strap endpoints meeting shoulder and bag, bag/hand/ground clearance, camera pitch, aim and framing.
**NOT RUN:** `bpy`/`bmesh` execution, mesh and modifier results, GLB export, `.blend` save, Cycles render, Godot import.

**Environment limits:** This remote session has git and Python 3, no Blender or Godot binary. Their presence on the user's PC is unverified from here.

**Next step:** Run the generator in real Blender with `--render`, then judge the three visual points listed in `art/README.md`.
