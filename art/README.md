# Art Pipeline

Blender-Python-Generatoren für Spirit-Village-Figuren und -Gebäude. Jeder Generator ist
ein eigenständiges, reproduzierbares Skript unter `art/generators/`, das mit
Blender im Hintergrundmodus ausgeführt wird und `.blend`-Quelldateien sowie
`.glb`-Exporte für Godot erzeugt. Generatoren nutzen keine Add-ons, keine
externen Python-Pakete und keine heruntergeladenen Assets. Fremd-Assets (CC0)
gelangen nur über den Intake mit Herkunftsnachweis ins Spiel.

- **[PIPELINE.md](PIPELINE.md)** – Look, Assetquellen und Lizenzen, Figuren,
  Animation, Weg ins Spiel, Mobile-Budgets, Sessionplan.
- **[BLENDER_WORKFLOW.md](BLENDER_WORKFLOW.md)** – Arbeitsweise für
  Generatoren (Daten-API, visuelle Feedbackschleife, Prüfungen) und Blender MCP.

## creature_base.py — gemeinsamer Wesen-Grundkörper

Gemeinsamer Teil aller Wesen-Generatoren (seit S5): Körperprofil (Kugel mit
radialem Profil: `body_taper`, `body_taper_range`, `body_bottom_fullness`),
Füße, Hände (optional `hand_pitch_deg`, `hand_pivot_ratio`), Augen mit
Glanzpunkt (optional flach: `eye_depth_ratio`, `eye_tilt_deg`), Node-
Hierarchie mit Pivots (`SPEC["parents"]`, `body_pivot`, `bake_rotations`),
Prüfungen, GLB-Export und `--views`. Ein Wesen-Modul liefert `CONFIG`
(Farben als **sRGB** mit Materialnamen), eigene Teile und `SPEC` an
`creature_base.run()`.

Prüfungen bei jedem Lauf: Höhe und Bodenkontakt **über Vertices**,
Höhenbereich, Dreiecksbudget, Durchdringungen (`separate_parts`, BVH),
GLB-Inhalt (Node-Skalierung, Kameras/Lichter, Gesicht bei glTF +Z). Schlägt
eine fehl, schreibt der Lauf trotzdem alle Ausgaben und endet mit **Exit 1**.
Die Vorschaukamera rahmt die gemessenen Vertex-Grenzen.

## garden_wight.py — Gartenwicht (Player-Charakter)

Statischer, nichtmenschlicher Spielercharakter: ein gedrungener,
birnenförmiger Gartenwicht. Kappe, Beutel, Klappe und Riemen stehen in
`garden_wight.py`, alles andere in `creature_base.py`.

### Konventionen

- **Z-up**, beide Fußsohlen exakt auf `z = 0`, Höhe 0,90 m (über Vertices).
- **Blickrichtung −Y** in Blender. Blenders Frontansicht (Numpad 1) schaut
  von −Y nach +Y und zeigt das Gesicht. Augen, Riemen und Vorschaukamera
  verwenden dieselbe Vorderseite (`FRONT_SIGN`).
- **Im GLB zeigt das Gesicht nach glTF +Z** — geprüft in der exportierten
  Datei (Augen-Nodes bei z = +0,255). Das ist die glTF-Vorderseitenkonvention
  und entspricht in Godot `Vector3.MODEL_FRONT` (+Z), **nicht** der
  −Z-Vorwärtsrichtung von `Node3D`/`look_at()`. In Godot also
  `look_at(ziel, Vector3.UP, true)` verwenden oder das Modell um 180° drehen.
- **`.L`/`.R`** folgen Blenders Spiegelkonvention: linke Körperseite der
  Figur = +X.
- **Alle `CONFIG`-Maße sind volle Ausdehnungen** (Durchmesser, Länge,
  Breite, Höhe) — nie Radien. Teile werden per `bmesh` in Einheitsgröße
  erzeugt und auf diese Maße skaliert; die Skalierung steckt in den
  Mesh-Daten, nicht im Objekt. `body_width` ist also wirklich der größte
  Durchmesser des fertigen Körpers.
- Verhältniswerte (`*_ratio`) sind Anteile von `body_height`, gemessen ab dem
  tiefsten Punkt des Körpers.

### Gestaltung

- **Körper/Kopf**: ein einziges, parametrisch verformtes Mesh (Kugel →
  Birnenform über eine radiale Profilfunktion: untere Hälfte voll rund, obere
  Hälfte per Smoothstep um `PEAR_HEAD_TAPER` verjüngt). Die Profilfunktion wird
  normiert, sodass die breiteste Stelle exakt `body_width` misst. Kopf und
  Rumpf gehen bewusst ohne Nahtstelle ineinander über. Dieses Mesh dient
  zugleich als sichtbarer cremefarbener Überwurf — für die erste statische
  Version gibt es keine separate Kleidungsgeometrie.
- **Anbauteile aus der Körperoberfläche abgeleitet**: Augen, Hände, Beutel
  und Riemen werden über `body_radius_at()` an der tatsächlichen
  Oberfläche ihrer jeweiligen Höhe platziert. Ändert man `body_width` oder
  `body_height`, wandern sie mit, statt auseinanderzudriften.
- **Füße**: zwei kleine, dunkelbraune, abgeflachte Kugeln; Sohlen auf `z = 0`,
  Oberkante ragt in den Körper hinein, damit keine Lücke entsteht.
  `foot_forward` schiebt sie so weit nach vorn, dass die Spitzen in der
  50°-Vorschau unter dem Bauch sichtbar sind.
- **Hände**: zwei kurze, abgerundete Stubs ohne Finger, an der Flanke
  eingebettet und um `hand_forward` nach vorn versetzt; die unteren Enden
  spreizen leicht nach außen (hängende Haltung). Auf der Beutelseite bleiben
  sie frei von Beutel, Klappe und Riemen (automatisch geprüft).
- **Augen**: zwei dunkle Kugeln auf dem Rotationsquerschnitt der Kopfhöhe,
  um `eye_protrusion` nach außen versetzt, deutlich unterhalb der
  Kappenkrempe. Je ein kleiner weißer Glanzpunkt (`EyeShine.*`,
  `eye_shine_diameter`, 0 = aus), auf beiden Augen gleich oben und zur rechten
  Körperseite (−X) versetzt.
- **Kappe**: per bmesh direkt erzeugter Kegel entlang einer gekrümmten
  Mittellinie: gerade bis `cap_bend_start`, danach biegt sich die Spitze um
  `cap_bend_deg` zur Neigungsseite (+X). Kein Modifier. Objektursprung auf der
  Krempenmitte, `cap_lean_deg` kippt die Kappe um ihre Basis. Die Krempe
  ragt `cap_brim_width` über die Basis hinaus und hängt hinten und seitlich um
  `cap_brim_droop` herab; vorne ist der Überhang zu `cap_brim_front_lift`
  angehoben, damit die Augen frei bleiben. Lippe mit `cap_brim_thickness`,
  Unterseite geschlossen.
- **Samenbeutel**: abgerundeter Quader (Kanten per `bmesh`-Bevel,
  `bag_bevel`) an der Flanke gegenüber der Kappenneigung (−X), mit Klappe
  (`BagFlap`): Deckel plus vordere Lasche über `bag_flap_depth_ratio` der
  Beutelhöhe, im dunkleren Riemen-Ocker.
- **Riemen (Schultergurt)**: geschlossenes Band als Schlaufe auf der
  Beutelseite: von der Vorderkante des Beuteldeckels an der vorderen Flanke
  neben dem Gesicht hoch, über die Schulter (Scheitel bei 90°, Höhe
  `strap_shoulder_ratio`), an der hinteren Flanke hinunter zur Hinterkante des
  Beuteldeckels. Beide Enden reichen `strap_bury` in den Beutel hinein und
  verjüngen sich auf den letzten `strap_taper_length` über dem Deckel auf
  `strap_end_width`, damit sie in die 10 cm Beuteltiefe passen.
  `strap_path()` interpoliert Stützpunkte in (Winkel um den Körper, Höhe,
  Abstand zur Oberfläche) per Catmull-Rom; der Abstand wird auf ≥ 0 begrenzt,
  daher liegt kein Abschnitt im Körper. Die Rückseite spiegelt die vorderen
  Stützpunkte (`180° − Winkel`). `strap_mid_angle_deg` hält den vorderen Lauf
  zwischen Augen und Hand. Der Arm ragt durch die Schlaufe.
- **Materialien**: flache, matte Principled-BSDF-Materialien (hohe Rauheit,
  kein Metallic), keine Texturen. Farben stehen als sRGB in der `CONFIG`
  und werden linearisiert (vor S5 wurden lineare Werte eingetragen, die blass
  wirkten).
- **Mesh-Auflösung und Schattierung**: `body_segments`, `part_segments`,
  `cap_segments`, `strap_samples_per_span`; zusammen ca. 9 200 Dreiecke.
  Alles glatt schattiert; Beutel, Klappe, Riemen und Krempe behalten Kanten
  über `smooth_angle_deg` scharf.

Alle Maße, Positionen und Farben stehen zentral im `CONFIG`-Dict am
Skriptanfang; `derive_dimensions()` löst daraus alle konkreten
Weltkoordinaten auf.

### Annahmen / API-Ziel

- **Geprüft mit Blender 5.2.1 LTS** (Windows, `--background
  --factory-startup`, glTF-Exporter 5.2.40). Ältere Versionen (z. B. 4.5 LTS)
  sind ungetestet. `Material.use_nodes` wird nur vor 5.0 gesetzt (ab 5.0
  veraltet, Node-Materialien sind dort Standard).
- Das Skript geht von einer **leeren Factory-Startup-Szene** aus und räumt am
  Anfang (`clear_scene()`) alles aus der Szene. Deshalb **nur** in einem
  eigenen Hintergrundprozess ausführen, niemals in einer geöffneten
  Arbeitsdatei.
- Der `bpy`-Import ist bewusst weich: die reinen Geometriefunktionen
  (`derive_dimensions` und Hilfsfunktionen) lassen sich mit einem normalen
  Python-Interpreter importieren und rechnerisch prüfen. `main()` bricht ohne
  Blender weiterhin mit klarer Meldung ab.

### Verwendung

Argumente werden **nach** `--` gelesen (Blender-Konvention).

```bash
# Pfad zur Blender-Programmdatei ggf. anpassen, z. B. unter Windows
# "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

blender --background --factory-startup --python-exit-code 1 --python \
  art/generators/garden_wight.py -- \
  --output-dir build/characters/garden_wight --render
```

- `--output-dir <pfad>`: Zielverzeichnis (relative Pfade werden gegen das
  Arbeitsverzeichnis aufgelöst, aus dem Blender gestartet wurde). Standard:
  `build/characters/garden_wight`.
- `--render` (optional): erzeugt zusätzlich die PNG-Vorschau.
- `--views` (optional, schließt `--render` ein): Prüfsatz für die visuelle
  Feedbackschleife – `garden_wight_back.png` (50°), `garden_wight_side_bag.png`
  (Beutelseite, 20°) und `garden_wight_fig96px.png` / `garden_wight_fig48px.png`
  (Vorschau auf die Figur zugeschnitten, Figur 96 bzw. 48 px hoch). Gibt die
  Figurenhöhe im Vorschaubild aus.

Jeder Lauf führt die Prüfungen aus `creature_base.py` aus (u. a.
`SEPARATE_PARTS`, `WARNING intersection: …`); bei einem Fehler endet er
nach dem Schreiben aller Ausgaben mit Exit 1.

Erzeugte Dateien:

- `garden_wight.blend` — Charakter-Collection `GardenWight_Character` **und**
  Vorschau-Setup `GardenWight_PreviewSetup` (Boden, Sonne, orthografische
  Kamera; alles über `bpy.data` angelegt).
- `garden_wight.glb` — **ausschließlich** die Figur inklusive Materialien.
  Der Export läuft, bevor das Vorschau-Setup überhaupt existiert. Geprüft:
  14 Nodes (`GardenWight_Root` + 13 Mesh-Teile), 7 Materialien, keine
  Kameras, Lichter oder Boden, keine Node-Skalierung; Mesh-Namen entsprechen
  den Objektnamen.
- `garden_wight_preview.png` (mit `--render` oder `--views`), dazu die
  `--views`-Prüfbilder.

### Vorschaukamera und Renderweg

Die Kamera wird aus den gemessenen Vertex-Grenzen der gebauten Figur
berechnet, nicht von Hand gesetzt: Sie steht auf der Vorderseite (−Y), blickt
`preview_pitch_deg` (50°) unter dem Horizont genau auf die Mitte der Grenzen, und `ortho_scale` ergibt
sich aus der projizierten Höhe und Breite der Figur plus `preview_margin`.
Höhen- und Breitenbedarf werden dabei gegen das Hochformat-Seitenverhältnis
geprüft, damit die komplette Figur im Bild bleibt.

`configure_render()` setzt **Cycles mit `device = 'CPU'`** und wird
**vor** `save_as_mainfile()` aufgerufen. Die gespeicherte `.blend` und ein
eventuelles `--render`-PNG verwenden dadurch identische Einstellungen.
Begründung für CPU: die Pipeline setzt nirgends eine konfigurierte GPU
voraus; Cycles-CPU ist über Blender-Installationen hinweg der
portabelste Weg zu einem Standbild. Auf einer GPU-Maschine kann
`scene.cycles.device` bei Bedarf umgestellt werden — bewusst keine
Automatik.

### Stand und Prüfungen

**Bildhöhe vs. Figurenhöhe:** Die Vorschau ist 1024 px hoch, die Figur nimmt
darin 564 px ein (vom Generator ausgegeben). Kleinprüfungen beziehen sich auf
die **Figurenhöhe**.

S5 (Blender 5.2.1 LTS, Windows, Nutzer-PC; Protokoll lokal unter
`build/characters/garden_wight/run.log`):

- `--views`: Exit 0, Höhe über Vertices 0,901 m, Bodenkontakt 0,0000,
  9 190 Dreiecke (Budget 10 000), 0 von 15 Paaren durchdringen sich.
- GLB: 14 Nodes (flach unter `GardenWight_Root`), 13 Meshes, 7 Materialien,
  keine Kameras/Lichter, keine Node-Skalierung, `Eye.L` bei glTF z = +0,255.
- Gegen den Stand vor S5 verglichen: Node-Transformationen und alle
  Vertex-Positionen bitgleich; nur die Materialfarben haben sich geändert.
- Bilder angesehen (`docs/previews/garden_wight*.png`). **Vorher:** Kappe
  salbei-/mintgrün, Tasche blass khaki, Gurt sandfarben (lineare Werte als
  sRGB missverstanden). **Nachher:** Kappe Blattgrün, Tasche warmes Braun,
  Gurt Dunkelbraun, Überwurf Creme; im Lineup-Licht wie in `mockup.png`.
- Intake + `--verify` PASS, Godot-Import ohne Fehler (S5).

Offene visuelle Befunde:

1. **48 px Figurenhöhe:** Der Gurt ist kaum als Gurt lesbar.
2. **Hände** wirken aus der 50°-Kamera noch leicht wie seitliche Ohren.
3. **Knick am Beutel:** Der Gurt biegt über der Klappe deutlich in den
   senkrechten Lauf.
4. Unter dem grauen Vorschaulicht wirkt Creme leicht grau; im Lineup mit
   Spiellicht nicht.

## forest_spirit.py — Waldwesen (Helfer, `char_forest_spirit`)

Gedrungenes, moosgrünes Wesen mit zweiblättrigem Spross (Referenz:
Waldwesen links in `mockup.png`). Aufruf wie beim Gartenwicht, Ausgabe unter
`build/characters/forest_spirit/` (`forest_spirit.glb`, `.blend`, Vorschau,
`_back`, `_side`, `_fig96px`, `_fig48px`).

- **Körper:** Eiform, unten voller (`body_bottom_fullness` 0,75), oben leicht
  verjüngt (`body_taper` 0,08); 0,42 m breit.
- **Spross:** `Sprout` (Stiel aus dem Scheitel) mit `Leaf.L`/`Leaf.R`:
  geschlossene Blattflächen, an beiden Enden spitz, längs nach oben
  gewölbt, quer gemuldet, 55° nach außen gespreizt. Blattbasen liegen knapp
  unter der Stielspitze (keine Lücke in der Seitenansicht).
- **Augen:** flache Knöpfe (`eye_depth_ratio` 0,45), um 25° nach oben
  gekippt, auf 0,58 Körperhöhe. Kugelaugen höher am Kopf lugten in der
  Rückansicht (50°) über den Scheitel.
- **Hände:** runde Stummel, 80° nach vorn gerichtet (von oben keine
  „Flossen“); **Füße** dunkelbraun, Spitzen vorn sichtbar.
- **Animation ohne Skelett (S6):** `ForestSpirit_Root` → `Body` (Pivot am
  tiefsten Körperpunkt) und `Foot.L/R`; `Body` → `Eye.*` (→ `EyeShine.*`),
  `Hand.*` (Pivot nahe dem Ansatz), `Sprout` (Pivot am Stielfuß) → `Leaf.*`
  (Pivot an der Stielspitze). Alle Node-Rotationen 0; im Spiel-GLB geprüft.

Stand S5: `--views` Exit 0, Höhe 0,653 m, Bodenkontakt 0, 4 648 Dreiecke
(Budget 6 000), 0 von 10 Paaren; GLB 13 Nodes, 12 Meshes, 6 Materialien,
keine Node-Skalierung, Gesicht +Z. Alle Bilder angesehen
(`docs/previews/forest_spirit*.png`): bei 48 px Figurenhöhe grünes Wesen mit
Spross und Augen lesbar. Iterationen: Spross vergrößert (war bei 48 px
unsichtbar), Hände nach vorn (wirkten wie Flossen), Augen abgeflacht und
gekippt (Rückansicht). Offen: Gesicht sitzt aus 50° eher tief; kein Mund,
keine Moosstruktur.

## Gebäude

### bldg_cottage.py — Wurzelheim-Häuschen

Rundes Häuschen nach `PIPELINE.md` 4a: cremeweiße Putzwand (leicht
ausgestellter Fuß) auf einem Steinsockel, überstehendes Kuppeldach aus sieben
Terrakotta-Schindelringen mit flachen, abgerundeten Ziegelzungen (je Ziegel
einer von drei Terrakottatönen), Rundbogentür aus fünf Planken mit Eisenring,
Holzrahmen, Rundfenster mit Sprossenkreuz, Wandlaterne am Eisenarm, zwei
Steinstufen aus nach oben verjüngten Feldsteinen. Wand 2,1 m hoch, Ø 2,4 m;
Dach Ø 2,8 m, 0,85 m hoch; Tür 1,3 m. Ca. 7 100 Dreiecke (Budget 8 000), 13
Materialien, keine Texturen.

**Konventionen** (zusätzlich zu PIPELINE.md Abschnitt 2):

- Z-up in Blender, Tür nach −Y → im GLB nach **+Z**; Bodenkontakt z = 0,
  Ursprung in der Mitte der Standfläche.
- Tür, Rahmen und Fenster werden in Wandkoordinaten angelegt (`u` =
  Bogenlänge, `v` = Höhe, `depth` = Abstand vor dem Putz) und über
  `wall_point()` auf die gewölbte Wand gelegt. Tür- und Fensterkanten liegen
  hinter einer Rahmenlippe, damit keine Lücke und keine Durchdringung
  entsteht.
- **Farben in `CONFIG` sind sRGB** (wie ein Farbwähler oder Godots
  `albedo_color`) und werden für Blender/GLB linearisiert. Der Gartenwicht
  verwendet noch lineare Werte.
- Nodes: `Cottage_Root` → `Walls`, `Base`, `Roof`, `Door`, `DoorFrame`,
  `Window`, `Lantern` (→ leerer `LanternLight` als Lichtanker), `Steps`.
  `Door` hat seinen Ursprung auf der Scharnierkante (−X), Drehung um die
  Hochachse öffnet sie.
- Das Dach ist auf die 50°-Spielkamera abgestimmt: Die Traufe muss höher
  hängen als etwa Überstand × tan 50° über dem Türrahmen, sonst verdeckt sie
  die Türoberkante (erster Lauf: 0,3 m Überstand, Tür halb verdeckt).
- Aus 50° wirkt die Dachfläche etwa `Dach-Ø × sin 50° + Dachhöhe × cos 50°`
  hoch, die sichtbare Wand nur `Wandhöhe × cos 50°`. Mehr Wand im Bild gibt es
  deshalb nur über eine höhere Wand und einen kleineren Dachdurchmesser, nicht
  über ein flacheres Dach.
- Die glatte Dachkappe (Spitze und drei Stützringe, zuerst erzeugt) bekommt
  die exakten Kuppelnormalen als eigene Normalen; interpolierte
  Fächer-Normalen zeigten radiale Streifen.

**Aufruf:**

```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background \
  --factory-startup --python-exit-code 1 --python art/generators/bldg_cottage.py -- \
  --output-dir build/buildings/bldg_cottage --views
```

`--render`: Vorschau 50°. `--views`: zusätzlich Rückseite (50°), Seite
Laternenseite (20°) und Größenvergleich mit dem Gartenwicht in
Spielkamera-Dichte (S1: 18 m Bildhöhe auf 800 px) als `_game1x` (logische
Pixel) und `_game3x` (≈ 1080 px breites Handy); braucht
`build/characters/garden_wight/garden_wight.glb`.

**Automatische Prüfungen** (jeder Lauf; Exit 1 bei Fehler, Dateien werden
vorher geschrieben): Dreiecke je Teil und gesamt gegen Budget, tiefster Punkt
= 0 ± 0,001, keine Objektskalierung, BVH-Durchdringung der Paare in
`SEPARATE_PARTS`, GLB-JSON (alle Nodes vorhanden, keine Skalierung, keine
Kameras/Lichter, `Door` bei glTF +Z). Die reinen Geometriefunktionen
(`derive_dimensions`, `roof_rows`, `step_stones`, `inspect_glb`) laufen ohne
Blender.

**Stand** nach Nacharbeit S8b (Blender 5.2.1 LTS, Nutzer-PC, `--views`):
Exit 0; 7 128 Dreiecke (GLB identisch), Höhe 2,96 m, tiefster Punkt 0,0000,
0 von 15 Paaren durchdringen sich, Door-Node glTF (−0,43; 0,19; 1,20). Bei 1×
ist das Häuschen 177 px hoch, der Gartenwicht 32 px. Alle fünf Bilder
angesehen, Kopien unter `docs/previews/bldg_cottage*.png`. Ausstehend
(NOT RUN): Godot-Import, Handy-Ansicht.

Behoben in S8b: Dach dominierte die Silhouette (Wand jetzt 2,1 statt 1,8 m,
Dach-Ø 2,8 statt 3,0 m, Dachhöhe 0,85 statt 1,0 m); Schindeln wirkten wie
dünne Blütenblätter (flachere Zungen, dickere Lippe und Traufe, dunkleres
Terrakotta mit Farbstreuung je Ziegel); radiale Streifen in der Kappe;
gleichförmige Stufen.

Offene visuelle Befunde:

1. Aus 50° ist das Dach noch die größte Fläche; weniger geht nur mit
   flacherer Spielkamera (Entscheidung zur Kamera, nicht zum Modell).
2. Die glatte Kappe liegt als kleiner flacher „Knopf“ auf dem obersten
   Schindelring; in Seiten- und Rückansicht sichtbar, aus der Spielkamera
   unauffällig.
3. Große glatte Wandflächen an Seite und Rückseite; die Referenz belebt sie
   mit Ranken und Pflanzen (Szenendekoration in S4, nicht im Generator).
