# Status

**Goal:** First static, non-human player character ("Garden Wight") as a reproducible Blender-Python generator; no Godot project, gameplay or animation yet.

**Implemented:**
- `art/generators/garden_wight.py` — standalone Blender script (factory-startup scene, pear-shaped body/head, hands, feet, eyes, asymmetric cap, seed bag + strap; GLB figure-only export; `.blend` with local preview setup; optional Cycles/CPU PNG render).
- `art/README.md` — design notes, config, usage, CPU render rationale, open review points.
- Root `README.md` — project pointer to the art pipeline.

**Checks:** `py_compile`/`ast.parse` on `garden_wight.py` — PASS. Arg-parsing/path logic (`--` splitting, `--output-dir` default, pathlib resolution) tested standalone — PASS. Script exits cleanly with a guidance message when run outside Blender — PASS.
**NOT RUN:** actual `bpy`/`bmesh` execution, GLB export, `.blend` save, Cycles render, Godot import — no Blender/Godot in this remote environment.

**Environment limits:** This remote session has git, Python 3, Xvfb; no Godot or Blender binary found. Blender/Godot presence on the user's PC is unverified from here.

**Next step:** Run `garden_wight.py` in real Blender (PC) with `--render`; visually review body silhouette, cap/eye occlusion, and strap plausibility per `art/README.md`; adjust `CONFIG` as needed.

Branch `claude/wurzelheim-env-audit-tmlfav`, commit `2a7072f`, not pushed.
