# Status

**Goal:** First static player character ("Garden Wight") as a reproducible Blender-Python generator. No Godot project, gameplay, rigging or animation yet.

**Implemented:**
- `art/generators/garden_wight.py` — standalone Blender script producing `.blend`, figure-only `.glb` and Cycles preview PNG. First real Blender run fixed body profile, cap geometry (bmesh, no modifier), surface-following strap, feet/hand placement, `.L`/`.R` naming.
- `art/README.md` — conventions, design, usage, verified state, open visual findings.
- `docs/previews/garden_wight.png` — real render (768×1024, 50° ortho).

**Checks (Blender 5.2.1 LTS, user PC, Windows):** generator with `--render` — PASS (exit 0, all three files written). Preview PNG viewed at full size, ~96 px and ~48 px — PASS for full figure, eyes, feet/ground contact, cap, strap. GLB JSON — PASS: 11 nodes (root + 10 meshes), 6 materials, no camera/light/ground; face on glTF +Z.
**NOT RUN:** Godot import; Blender versions other than 5.2.1.

**Open findings:** strap reads as an arc/mouth from 50°; eyes barely legible at ~48 px; Godot must treat +Z as model front (`look_at(..., true)` or 180° turn).

**Next step:** Godot import test, or visual tuning of strap/small-size readability.
