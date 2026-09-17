# Status

**Goal:** First static player character ("Garden Wight") as a reproducible Blender-Python generator. No Godot project, gameplay, rigging or animation yet.

**Implemented:**
- `art/generators/garden_wight.py` — standalone Blender script: `.blend`, figure-only `.glb`, Cycles preview PNG. Strap is a shoulder loop on the bag side (front flank → over shoulder → back flank), ends tapered and buried in the bag top.
- `art/README.md` — conventions, design, usage, executed vs. pending checks, open findings.
- `docs/previews/` — real renders: front preview, back, bag side, crops at 96/48 px figure height.

**Checks (Blender 5.2.1 LTS, user PC):** generator `--render` — PASS (exit 0, three files). Front/back/side renders viewed — PASS: eyes clear, no arc under eyes, continuous loop, no free ends or visible sinking. 96 px figure height — PASS; 48 px — not mouth-like, strap barely legible. GLB JSON — PASS: 11 nodes, 6 materials, no camera/light/ground, face on glTF +Z.
**NOT RUN:** Godot import; other Blender versions.

**Open findings:** kink where the strap leaves the bag top; strap weak at 48 px figure height; Godot must treat +Z as model front.

**Next step:** Godot import test.
