# Art-Pipeline Spirit Village

Festlegung vom 2026-09-17. Legt fest, woher Modelle kommen, wie sie einen
gemeinsamen Look erhalten, wie sie animiert werden und wie sie automatisiert
ins Spiel gelangen. **✅** = festgelegt, **⚠** = offen mit Empfehlung (wird in
der genannten Session entschieden). Generator-Arbeitsweise und Blender MCP:
[BLENDER_WORKFLOW.md](BLENDER_WORKFLOW.md).

## 1. Look: „Verwunschener Miniaturgarten“ ✅

| Bereich | Vorgabe |
|---|---|
| Perspektive | Orthografische 3D-Kamera schräg von oben, Ausgangswert 50° nach unten, Hochformat |
| Bildaufbau | Eine überschaubare Lichtung/Terrasse, deutliche Wege, große Arbeitsstationen |
| Formen | Runde Baumkronen, kräftige Pilze, dicke Stämme, runde Häuschen mit Kuppeldach (siehe 4a) |
| Materialien | Matt, wenig Oberflächendetail, zurückhaltende Texturen |
| Farben | Moosgrün, Creme, warmes Holzbraun, Terrakotta; Blau und Orange nur als Akzent |
| Licht | Warmes Tageslicht, weiche Schatten, helle Schattenseiten |
| Naturwesen | Körperlich, greifbar, mit Gewicht; kleine Füße oder hüpfende Bewegung |
| Effekte | Blätter, Tropfen, Funken, Dampf – sparsam |
| UI | Ruhige cremefarbene Karten, klare Symbole, große Touch-Flächen |

Der Bezug zur Referenz (`mockup.png`, nur visuelle Referenz) entsteht über
Gemütlichkeit, Natur und kleine alltägliche Handlungen, nicht über eine
gemalte Oberfläche.

## 2. Konventionen für alle Spiel-Assets ✅

- **Format:** GLB (Godot-Empfehlung für 3D-Szenen; Skelette und Animationen
  bleiben erhalten).
- **Maßstab:** 1 Einheit = 1 m. Beetfeld = 1 × 1 m. Player ca. 0,95 m
  (aktueller Gartenwicht).
- **Ausrichtung:** Y-up im GLB. **Vorderseite = +Z** (glTF-Konvention, Godot
  `Vector3.MODEL_FRONT`); abweichende Quellmodelle werden beim Intake gedreht.
- **Ursprung:** Mitte der Standfläche, Bodenkontakt bei y = 0.
- **Knoten:** keine nicht-uniforme Skalierung; bewegliche Teile als eigene
  Nodes mit sprechenden Namen (`Hand.L`, `Cap` …).
- **Namen:** `snake_case`-Dateinamen, Präfix nach Kategorie
  (`char_`, `crop_`, `tree_`, `prop_`, `bldg_`).

## 3. Assetquellen und Lizenzen

Rohpakete liegen seit 2026-09-17 unter `D:\Mika\assets\quaternius\` (S0),
jeweils mit Lizenzdatei und `PROVENANCE.txt` (ZIP-Name, SHA-256, Datum).

| Einsatz | Paket (Quaternius, CC0 1.0 laut Lizenzdatei) · Ordner | Rolle |
|---|---|---|
| Bäume, Büsche, Farn, Blumen, Gras, Pilze, Felsen, Kiesel, Steinpfade | Stylized Nature MegaKit, Standard (68/116 Modelle) · `stylized_nature_megakit\standard_2026-09-17\` | Hauptbasis Umgebung ✅; Steinpfade auch für Stufen. Anbieter-Shader nur in Source-Edition |
| Feldfrüchte (u. a. Karotte, Kürbis, Salat, Rübe) | Ultimate Crops, Download „Nature Crops Pack – Jan 2020“ · `ultimate_crops\2020-01\` | Hauptbasis Beete ✅ |
| Kleinteile: Fass, Holzeimer, Kisten, Gemüsekisten, Topf, Kessel, Wandlaterne, Bank, Hocker, Werkbank, Axt | Fantasy Props MegaKit, Standard · `fantasy_props_megakit\standard_2026-09-17\` | wenige gezielt gewählte Teile ✅; Stil realistischer (Trim-Texturen mit Normal/ORM) → beim Intake auf matte Palettenfarben abbilden |
| Gebäude, Arbeitsstationen | – | **eigene Generatoren** ✅ (siehe 4a) |
| Naturwesen | Ultimate Monsters · `ultimate_monsters\2026-09-17\` | nur einzelne Pilzwesen als Vergleichskandidat |
| – | Farm Buildings (Sept 2018) · `farm_buildings\2018-09\` | **nicht verwendet** ❌: rote US-Scheunen, Silos, Windräder, flacher Low-Poly-Stil – widerspricht der Referenz; höchstens Platzhalter |
| Menschlicher Player | Ultimate Modular Men/Women (nicht heruntergeladen) | nur falls Variante C (siehe 4) |

Regeln:

- **CC0 heißt nicht „alles kostenlos“:** Teile der Pakete liegen in
  kostenpflichtigen Editionen. Pro Download werden Edition, Version, Datum und
  Lizenztext festgehalten; die Lizenz wird beim Download erneut geprüft.
- **Herkunftsnachweis** für jedes im Spiel verwendete Asset in
  `art/ASSETS.md`: Spieldatei, Quellpaket, Edition/Version, Quelldatei,
  Lizenz, Änderungen (Skalierung, Drehung, Materialtausch).
- ✅ **Rohdownloads außerhalb von Git** unter `D:\Mika\assets\<anbieter>\<paket>\<version>\`,
  im Intake-Manifest über die Umgebungsvariable `SV_ASSET_SOURCE`
  (= `D:\Mika\assets`) referenziert. Ins Repo kommen nur die verarbeiteten
  GLBs, die das Spiel nutzt. Grund: Die fünf Pakete sind entpackt ca. 560 MB;
  Git soll Spiel und Pipeline versionieren, nicht Bibliotheken.
- Keine Assets über die Online-Dienste des MCP-Addons und keine KI-Mesh-Generierung
  ohne eigene Entscheidung.

## 4. Figuren

**Player** ⚠ – Entscheidung im Vergleich (Session S3), in Smartphone-Größe:

| Variante | Basis | Stärke | Schwäche |
|---|---|---|---|
| **A** Gartenwicht, per Skript | `art/generators/garden_wight.py` (existiert, ca. 9 200 Dreiecke) | Eigenständig, trifft rundlichen Referenzlook, voll parametrisch | Keine Kleidung, keine menschlichen Arbeitsanimationen |
| **B** Gartenwicht auf Pilzwesen-Basis | Quaternius Ultimate Monsters | Fertige Form, evtl. vorhandene Animationen | Paketstil passt nur teilweise zum Ton |
| **C** Menschlicher Gärtner | Ultimate Modular Men (Bauer) | Skelett und Animationen vorhanden | Kantig und länglich, verfehlt den Referenzlook |

**Empfehlung: A als Hauptkandidat, B als direkter Vergleich, C nur auf
ausdrücklichen Wunsch.** Das deckt sich mit der Projektvorgabe „originale,
rundliche, nichtmenschliche Gartenwesen“ (AGENTS.md). Die Vorgabe „nur
fertige Assets, keine Modellierarbeit“ gilt nicht für Figuren: A ist per
Skript erzeugt, also reproduzierbar, aber eine eigene Erstellung.

**Spirits** ✅ – gemeinsame Gestaltungsvorlage, wenige Grundkörper:

| Wesen | Designziel | Bewegung |
|---|---|---|
| Waldwesen | Gedrungen, moosfarben, Blatt- oder Pilzmotiv | Kurze Schritte, neugieriges Neigen |
| Feuerwesen | Warme Farben, kompakte Silhouette, wenige Funken | Federndes Hüpfen |
| Wasserwesen | Rund, blau, Tropfenmotiv | Sanftes Schaukeln |

Es gibt kein passendes fertiges CC0-Set. Deshalb gibt es einen gemeinsamen,
per Skript erzeugten Grundkörper (Weiterentwicklung der Gartenwicht-Geometrie);
Varianten entstehen über `CONFIG` (Farben, Anbauteile, Proportionen). **Zuerst
ein überzeugendes Waldwesen**; Feuer und Wasser erst nach dessen Abnahme.

## 4a. Gebäude und Arbeitsstationen ✅

Kein heruntergeladenes Paket trifft die Referenz. Gebäude und Stationen
entstehen deshalb **per Blender-Skript** wie der Gartenwicht (Arbeitsweise
[BLENDER_WORKFLOW.md](BLENDER_WORKFLOW.md), Budget ≤ 8 000 Dreiecke je Haus).
Formen sind einfach und rund, das passt zur Figurengeometrie.

| Objekt (Referenz `mockup.png`) | Merkmale | Priorität |
|---|---|---|
| Wurzelheim-Häuschen `bldg_cottage` | runder Baukörper aus cremeweißem Putz, gewölbtes Dach aus Terrakotta-Schindeln mit Überstand, runde Holztür mit Bogen und Ring, Rundfenster mit Sprossenkreuz, Wandlaterne, Steinstufen | 1 (Meilenstein 1) |
| Steinofen mit Kessel `bldg_oven` | gemauerter runder Sockel mit Feueröffnung, Kessel oben | 2 (Station Meilenstein 1) |
| Brunnen `bldg_well` | runder Steinring, Wasserfläche, hölzerne Kurbel | 3 |
| Holzunterstand `bldg_woodshed` | Pultdach auf Pfosten, Holzstapel | 4 |
| Zaun, Laternenpfahl, Blatt-Schild `prop_fence`, `prop_lamppost`, `prop_sign` | grobes Holz, Pfosten mit Querlatten | 4 |
| Riesenbaum mit Wurzeln | nur als Stamm-/Wurzelstück am Szenenrand andeuten | später |

- Bewegliche oder austauschbare Teile als eigene Nodes (z. B. `Door`,
  `Lantern`, `Smoke` als Ankerpunkt), damit Godot sie animieren kann.
- Vorhandene Kleinteile (Fass, Eimer, Kessel …) aus Fantasy Props bevorzugt
  über den Intake statt neu erzeugen.
- Der gemalte Render-Look der Referenz (weiches globales Licht,
  Tiefenunschärfe, Moosdetails) ist auf dem Handy nicht 1:1 erreichbar;
  angenähert wird er über warmes Licht, Farbverläufe und angedeutete
  Verschattung in den Materialien.

## 5. Animation ✅

- **Nichtmenschliche Wesen: ohne Skelett.** Bewegung über die Transformationen
  der Teil-Nodes in Godot (`AnimationPlayer`/`Tween`): Wippen, Neigen, Hüpfen,
  Stauchen/Strecken, Handstummel schwingen. Passt zu starren, rundlichen Teilen
  und spart Rigging.
- **Grundsatz für den Anfang:** Warten, Bewegen, Arbeiten, Freuen.
- Ein einfaches Skelett nur, wenn Verformung nötig wird (z. B. biegsame Kappe).
- Nur Variante C: Quaternius-Skelett plus Universal Animation Library 2
  (enthält Farming-Animationen). Verfügbarkeit im Download und Übertragung
  vorher praktisch prüfen.

## 6. Automatisierter Weg ins Spiel

```
Quellen                     Aufbereitung (Blender, Hintergrund)         Godot 4.6
art/generators/*.py   ─┐
                       ├─► GLB normalisiert (+Z, y=0, 1 m, Namen) ─► game/assets/…  ─► Post-Import-Skript
Rohpakete (außerhalb) ─┘   + Herkunftsnachweis art/ASSETS.md              (Materialien, Schatten)
                                   │
                                   ├─► Lineup-Renders (gleiches Licht/Kamera, Handygröße)
                                   └─► Inventar-Icons aus den Spielmodellen
```

1. **Auswahl klein halten:** 1 Player, 1 Helfer, 3 Pflanzen, 3 Bäume, 1 Haus,
   1 Arbeitsstation.
2. **Intake per Skript** (`art/tools/intake.py` + Manifest
   `art/intake_manifest.json`): importieren, drehen/skalieren, Boden auf y = 0,
   Materialien auf die gemeinsame Palette abbilden, GLB schreiben,
   Dreiecke melden, `art/ASSETS.md` aktualisieren.
3. **Lineup-Szene** (`art/tools/lineup.py`): alle Kandidaten unter einem Licht
   und einer Kamera; Bilder bei realer Handygröße; Silhouette, Größe, Farbe
   beurteilen. Ein Shader gleicht Farben an, aber keine Proportionen.
4. **Godot-Import automatisieren:** gemeinsames Post-Import-Skript (geteilte
   Materialien, Schattenwurf nur für Figuren und große Objekte); Import
   headless über
   `D:\Mika\tools\godot\Godot_v4.6-stable_win64.exe --headless --import`.
5. **Icons** (`art/tools/render_icons.py`): feste Kamera, transparenter
   Hintergrund, aus denselben GLBs.
6. **Abnahme auf dem Handy:** Figuren, Pflanzen und Aktionen bei normaler
   Spielgröße verständlich, Szene flüssig. Erst danach Inhalt erweitern.

Computer Use nur für Editor-Bedienung und Sichtkontrolle; Import, Konvertierung
und Exporte laufen über Skripte.

## 7. Mobile-Startbudgets (zu messen, noch nicht verifiziert)

| Größe | Startwert |
|---|---|
| UI-Entwurfsfläche | 360 × 800 logische Einheiten, Hochformat, anpassbar |
| Bildrate | stabile 30 FPS; höher erst nach Messung auf Zielgeräten |
| Player | ≤ 10 000 Dreiecke (Gartenwicht: ca. 9 200) |
| Helfer/Spirit | ≤ 6 000 Dreiecke |
| Pflanze je Wachstumsstufe | ≤ 1 500 Dreiecke |
| Baum / Haus | ≤ 4 000 / ≤ 8 000 Dreiecke |
| Texturen | 512–1024 px pro Texturset, nach Bildschirmgröße des Objekts |
| Licht | 1 gerichtetes Licht mit Schatten; wenige transparente Effekte |

Geometrie-, Textur- und Bildschirmauflösung werden getrennt betrachtet; es gibt
keine einheitliche „Modellauflösung“.

## 8. Projektstruktur ✅

Godot-Projekt unter **`game/`** (Godot 4.6, angelegt in S1). `art/`, `build/`
und `docs/` liegen damit außerhalb von `res://` und werden nicht importiert.
Verarbeitete Assets: `game/assets/{characters,crops,nature,props,buildings}/`.

## 9. Meilenstein 1: kleine Garten-Szene

Ziel: **Player, ein arbeitendes Naturwesen, ein wachsendes Beet** in einer
Godot-Szene, auf dem Handy abgenommen. Beantwortet, ob die Assets den Charme
der Referenz erreichen und welche Player-Variante trägt.

Sessions sind einzeln ausführbar. **Ausführung:** *Claude* = Claude Code;
*DeepSeek* = DeepSeek V4.1 Flash in OpenCode (gleicher Repo-Zugriff). Pro
Datei ein Schreiber; parallele Sessions nur bei getrennten Schreibbereichen.
Alle Sessions: Branch `claude/wurzelheim-env-audit-tmlfav`, Handoff als
Chat-Antwort im Format von AGENTS.md (keine Handoff-Datei),
`docs/STATUS.md` aktualisieren. Vor dem Commit `git pull --ff-only`; laufen
Sessions parallel, wird `docs/STATUS.md` beim Pull zusammengeführt statt
überschrieben.

| # | Session | Ausführung | Abhängig von | Stand |
|---|---|---|---|---|
| S0 | Pakete herunterladen und ablegen | Nutzer, manuell | – | ✅ 2026-09-17 |
| S1 | Godot-Projekt-Grundgerüst | DeepSeek · medium | – | ✅ `025546e` |
| S2 | Intake-Skript und Herkunftsnachweis | DeepSeek · medium, Review Claude · low | S0, S1 | ✅ `3cb4625` |
| S3 | Lineup und Player-Entscheidung | Claude · high | S2 | offen |
| S4 | Garten-Szene in Godot | DeepSeek · medium, Sichtprüfung Claude · medium | S2, S3, S8, S9 | offen |
| S5 | Gemeinsamer Wesen-Grundkörper + Waldwesen | Claude · high | S3 | offen |
| S6 | Prozedurale Animationen | DeepSeek · medium, Sichtprüfung Claude · low | S4, S5 | offen |
| S7 | Icon-Renderer | DeepSeek · low | S2 | offen |
| S8 | Gebäude-Generator: Wurzelheim-Häuschen | Claude · high | – | ✅ `4e1b8d0`, Nacharbeit S8b |
| S9 | Station: Steinofen mit Kessel | DeepSeek · medium, Sichtprüfung Claude · medium | S8 | offen |
| S8b | Häuschen-Nacharbeit: Dach und Stufen | Claude · medium | S8 | ✅ |

### S0 – Pakete ablegen (Nutzer) ✅

Erledigt: fünf Pakete unter `D:\Mika\assets\quaternius\` (Ordner und Editionen
in Abschnitt 3), `SV_ASSET_SOURCE=D:\Mika\assets` als Benutzervariable
gesetzt (gilt in neu gestarteten Terminals).

### S1 – Godot-Grundgerüst (DeepSeek · medium) ✅

Erledigt in `025546e`: `game/project.godot` (Mobile, 360 × 800,
`canvas_items`/`expand`, Hauptszene `res://scenes/garden.tscn`),
Asset-Ordner, `game/.godot/` ignoriert. `garden.tscn`: orthografische Kamera
(50°, `size` 18, Abstand 12 m zum Ursprung), warmes Richtungslicht mit
Schatten, `WorldEnvironment`, 8 × 8-m-Boden. Geprüft: `--import` und
`--quit-after 5` (Godot 4.6 verlangt eine Zahl) ohne Fehler.
Befund für S4: Die Kamera nutzt `keep_aspect` = Höhe; auf schmaleren Handys
als 9:20 wird der 8-m-Bereich seitlich beschnitten → auf Breite umstellen.

### S2 – Intake (DeepSeek · medium)

- **Ist:** Konventionen Abschnitt 2; Herkunftsregeln Abschnitt 3; Blender
  5.2.1: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`;
  Arbeitsweise `art/BLENDER_WORKFLOW.md` (Daten-API, keine
  `bpy.ops`-Geometrie, `--factory-startup --background --python-exit-code 1`).
- **Aufgabe:** `art/tools/intake.py` (Blender-Hintergrundskript) liest
  `art/intake_manifest.json` (Einträge: `id`, `source` relativ zu
  `$SV_ASSET_SOURCE`, `target` unter `game/assets/`, `rotate_y_deg`, `scale`,
  `material_map`, `license`, `edition`). Pro Eintrag: importieren (glTF/FBX/OBJ),
  Transformationen anwenden, Standfläche auf y = 0 und Mitte, Vorderseite +Z,
  GLB exportieren, Dreiecke und Materialien ausgeben; `art/ASSETS.md`
  tabellarisch neu schreiben. Zusätzlich der Gartenwicht aus
  `build/characters/garden_wight/garden_wight.glb` als Eintrag ohne
  Drittquelle.
- **Abnahme:** Lauf über 3 reale Modelle (1 Pflanze, 1 Baum, 1 Pilzwesen) plus
  Gartenwicht, Exit 0; je GLB: Bodenkontakt y = 0 (Bounding Box min y ±0,001),
  keine Node-Skalierung, Dreiecke im Budget oder als Befund gemeldet.
- **Schreibbereich:** `art/tools/intake.py`, `art/intake_manifest.json`,
  `art/ASSETS.md`, `game/assets/**`, `docs/STATUS.md`.

### S3 – Lineup und Player-Entscheidung (Claude · high)

- **Ist:** Intake-GLBs unter `game/assets/` (Liste und Dreiecke in
  `art/ASSETS.md`); Varianten A/B/C (Abschnitt 4); Häuschen
  `build/buildings/bldg_cottage/` (2,77 m). Befunde aus S2 zum Einbeziehen:
  `char_garden_wight` misst nach Intake 0,901 m statt der dokumentierten
  0,95 m (prüfen, ob `build/`-GLB veraltet oder die Angabe falsch ist);
  `crop_carrot_2` ist niedriger als Stufe 1; `tree_common_1` 6 265 Dreiecke
  (> 4 000); Godot extrahiert eingebettete Texturen zusätzlich als PNG
  (Baum und Fass je ca. 1,5 MB doppelt) → Import-Einstellung klären.
- **Aufgabe:** `art/tools/lineup.py`: Kandidaten nebeneinander auf einem
  1-m-Raster, gleiche Kamera (ortho, 50°) und gleiches Licht wie
  `garden_wight.py`; Renders in Handy-Darstellungsgröße (Figur 96 und 48 px).
  Visuell bewerten (Silhouette, Größe zu Pflanzen und Häusern, Farben);
  Player-Variante und Größenverhältnisse festlegen; Abschnitt 4 hier
  aktualisieren.
- **Abnahme:** Renders unter `docs/previews/lineup_*.png`, begründete
  Entscheidung.

### S4 – Garten-Szene (DeepSeek · medium)

- **Aufgabe:** In `game/scenes/garden.tscn` eine Lichtung aus Intake-Assets
  aufbauen: Wege, 3 × 3-Beet, 3 Bäume, Häuschen (S8), Steinofen (S9), Player
  an fester Position, 1 Helfer. Generierte GLBs aus `build/` kommen als
  Manifest-Einträge ohne Drittquelle über den Intake nach `game/assets/`.
  Kamera auf `keep_aspect` = Breite umstellen (Befund S1). Pflanzen wechseln per Skript
  (`game/scripts/crop_plot.gd`) durch 5 Wachstumsstufen. Post-Import-Skript
  `game/scripts/import/shared_materials.gd` gemäß Abschnitt 6.4.
- **Abnahme:** Headless-Start ohne Fehler; Screenshot im Hochformat
  (`docs/previews/garden_scene.png`); FPS-Messung auf dem PC als Richtwert.
  Sichtprüfung durch Claude.

### S5 – Wesen-Grundkörper und Waldwesen (Claude · high)

Grundkörper aus `garden_wight.py` in ein gemeinsames Modul überführen;
Gartenwicht und Waldwesen als Konfigurationen; Abnahme nach
`BLENDER_WORKFLOW.md` Abschnitt 3 (`--views`, keine Durchdringungen,
Budget ≤ 6 000 Dreiecke für das Waldwesen).

### S6 – Animationen (DeepSeek · medium)

Warten, Bewegen, Arbeiten, Freuen als `AnimationPlayer`-Clips auf den
Teil-Nodes (Abschnitt 5); Aufnahme als kurze Bildfolge für die Sichtprüfung.

### S7 – Icons (DeepSeek · low)

`art/tools/render_icons.py`: pro GLB ein 256-px-PNG mit transparentem
Hintergrund, feste 3/4-Kamera, gleiches Licht; Ausgabe
`game/assets/icons/`.

### S8 – Gebäude-Generator: Wurzelheim-Häuschen (Claude · high)

- **Ist:** Kein Gebäude im Repo. Vorbild für Aufbau und Prüfungen:
  `art/generators/garden_wight.py` (`CONFIG`-Block, bpy-freie
  Maßableitung, `bmesh`-Teile, `SEPARATE_PARTS` + BVH-Durchdringungsprüfung,
  `export_glb`, `--render`/`--views` mit Figurenhöhen-Zuschnitten).
  Arbeitsweise und Blender-Aufruf: `art/BLENDER_WORKFLOW.md`. Konventionen:
  Abschnitt 2; Budget ≤ 8 000 Dreiecke; Merkmale: Abschnitt 4a, Referenz
  `mockup.png` (oben links, ungetrackte Datei im Arbeitsverzeichnis).
  Gartenwicht-GLB zum Größenvergleich:
  `build/characters/garden_wight/garden_wight.glb` (0,95 m hoch; bei Bedarf
  neu erzeugen).
- **Aufgabe:** Neuer Generator `art/generators/bldg_cottage.py` (keine
  Änderung an `garden_wight.py`; gemeinsames Modul erst in S5). Startwerte,
  in der Session visuell festzulegen: Grundkreis Ø ca. 2,6 m, Wandhöhe ca.
  1,6 m, Kuppeldach mit Überstand und Schindelringen, Gesamthöhe ca. 3 m,
  Tür ca. 0,8 × 1,3 m zur +Z-Seite, Rundfenster seitlich vorn, Wandlaterne,
  zwei Steinstufen. Teil-Nodes u. a. `Walls`, `Roof`, `Door`, `Window`,
  `Lantern`, `Steps`. Ausgabe `build/buildings/bldg_cottage/`.
- **Abnahme:** Blender-Lauf Exit 0; Renders Vorschau 50°, Rückseite,
  Seitenansicht sowie ein Größenvergleich neben dem Gartenwicht in
  Spielkamera-Größe (Kamera S1: 18 m Bildhöhe auf 800 px) unter
  `docs/previews/bldg_cottage*.png`, jedes Bild angesehen; keine
  Durchdringungen zwischen getrennten Teilen; ≤ 8 000 Dreiecke;
  Bodenkontakt y = 0; keine Node-Skalierung; Tür zeigt nach +Z.
- **Schreibbereich:** `art/generators/bldg_cottage.py`,
  `docs/previews/bldg_cottage*.png`, `art/README.md` (Abschnitt Gebäude),
  `docs/STATUS.md`.

### S9 – Station: Steinofen mit Kessel (DeepSeek · medium)

- **Ist:** `art/generators/bldg_cottage.py` aus S8 als Vorlage (Aufbau,
  Prüfungen, Palette). Merkmale Abschnitt 4a.
- **Aufgabe:** `art/generators/bldg_oven.py`: runder gemauerter Sockel
  (Ø ca. 0,9 m, Höhe ca. 0,7 m) mit Feueröffnung nach +Z, Kessel oben,
  Teil-Nodes `Base`, `FireOpening`, `Cauldron`, `SteamAnchor` (leerer Node
  als Ankerpunkt für Dampf). Budget ≤ 4 000 Dreiecke. Ausgabe
  `build/buildings/bldg_oven/`.
- **Abnahme:** wie S8 (Renders `docs/previews/bldg_oven*.png` mit
  Größenvergleich zum Gartenwicht); danach Sichtprüfung durch Claude.
- **Schreibbereich:** `art/generators/bldg_oven.py`,
  `docs/previews/bldg_oven*.png`, `docs/STATUS.md`.

### S8b – Häuschen-Nacharbeit (Claude · medium)

- **Ist:** `art/generators/bldg_cottage.py` (S8, 7 128 Dreiecke), Renders
  `docs/previews/bldg_cottage*.png`, offene Befunde in `art/README.md`
  Abschnitt Gebäude. Sichtprüfung gegen `mockup.png`: Das Dach nimmt aus
  50° über die Hälfte der Silhouette ein und wirkt wie ein Pilzhut; die
  sieben dünnen, stark gewellten Schindelringe lesen sich eher wie
  Papier-/Blütenblätter als wie Ziegel; Stufensteine gleichförmig.
- **Aufgabe:** Wand höher bzw. Dach flacher mit geringerem Überstand, sodass
  Wand und Tür in der Spielkamera deutlich mehr Fläche haben (Referenz:
  Wand ≈ Dachhöhe); Schindeln dicker, weniger gewellt, dunkleres
  Terrakotta mit leichter Farbstreuung pro Ziegel, sichtbare Traufkante;
  radiale Schattierungslinien der Dachkappe beheben; Stufen unregelmäßiger.
  Budget weiter ≤ 8 000 Dreiecke.
- **Abnahme:** wie S8, Vorher/Nachher im Handoff benannt.
- **Schreibbereich:** `art/generators/bldg_cottage.py`,
  `docs/previews/bldg_cottage*.png`, `art/README.md` (Abschnitt Gebäude),
  `docs/STATUS.md`. Nicht parallel zu S9 an denselben Dateien.

## 10. Offene Entscheidungen

1. Player-Variante A/B/C (S3; Empfehlung A).
2. Kostenlose oder kostenpflichtige Paketeditionen (Empfehlung: erst kostenlos,
   nach der Lineup-Abnahme gezielt ergänzen; für die Umgebung wäre die
   Source-Edition des Stylized Nature MegaKit der erste Kandidat).

Entschieden am 2026-09-17: Rohdownloads außerhalb von Git
(`D:\Mika\assets`), Godot-Projekt unter `game/`, Farm Buildings nicht
verwenden, Gebäude per Generator.
