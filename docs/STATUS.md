# Status

**Goal:** Milestone 1 – Godot garden scene with player, one working spirit and a growing bed, accepted on a phone.

**Implemented:**
- `art/PIPELINE.md` — direction, conventions, CC0 sources, generator buildings, size ratios (4b), budgets, sessions S0–S9.
- S0/S1: packs outside Git; Godot 4.6 `game/`.
- S2: `intake.py` + manifest + `art/ASSETS.md`.
- S3: `lineup.py`; **player = Garden Wight (A)**, 0.90 m.
- S5: `creature_base.py`; **forest spirit** 0.65 m, 4,648 tris.
- S4a/S4b: trees/bush, cottage/oven, `garden.tscn`, `crop_growth.gd`/`crop_plot.gd`, `capture.gd`, post-import `shared_materials.gd`.
- **S4c:** ground 40×40 (no background band); cottage/oven fully framed with margin; barrel at the door; 14 path plates door→beet→oven; 38 greenery, 16 pebbles, 1 boulder in `Path`/`Greenery`/`Rocks`; sun x −62°, `light_angular_distance` 1.5, no shadow bars over the beet; trees moved clear of the buildings. 14 dressing GLBs via intake (grass, flowers, clover, mushroom, pebbles, rock, 4 rockpath).
- S7: `render_icons.py`; 10 icons + sheet.

**Checks:** intake exit 0, 14/14 `--verify` PASS; `--import` 0 ERROR; crop tests 6/6 PASS; `--quit-after 120` 0 ERROR; capture 360×800, 60.0 FPS, 97,979 triangles/frame (budget 150 000).
**NOT RUN:** phone tests.

**Findings:** S7 crops (thin seedlings) cover 6–12 % of the icon, below the 15 % floor.
**Next step:** S6 animations, phone acceptance.
