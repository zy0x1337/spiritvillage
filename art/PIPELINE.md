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
| Formen | Runde Baumkronen, kräftige Pilze, dicke Stämme, einfache Häuser |
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

| Einsatz | Paket (Quaternius, laut Anbieter CC0) | Rolle |
|---|---|---|
| Bäume, Büsche, Felsen | Stylized Nature MegaKit | Hauptbasis Umgebung ✅ |
| Feldfrüchte | Ultimate Crops (102 Modelle, 5 Wachstumsstufen) | Hauptbasis Beete ✅ |
| Werkzeuge, Kisten, Einrichtung | Fantasy Props MegaKit | wenige gezielt gewählte Teile ✅ |
| Hofgebäude | Farm Buildings | erster Hof ✅; bodenständiger als die Pilzhaus-Referenz |
| Naturwesen | Ultimate Monsters | nur einzelne Pilzwesen als Vergleichskandidat |
| Menschlicher Player | Ultimate Modular Men/Women | nur falls Variante C (siehe 4) |

Regeln:

- **CC0 heißt nicht „alles kostenlos“:** Teile der Pakete liegen in
  kostenpflichtigen Editionen. Pro Download werden Edition, Version, Datum und
  Lizenztext festgehalten; die Lizenz wird beim Download erneut geprüft.
- **Herkunftsnachweis** für jedes im Spiel verwendete Asset in
  `art/ASSETS.md`: Spieldatei, Quellpaket, Edition/Version, Quelldatei,
  Lizenz, Änderungen (Skalierung, Drehung, Materialtausch).
- ⚠ **Rohdownloads außerhalb von Git** – Empfehlung: `D:\Mika\assets\<anbieter>\<paket>\<version>\`,
  im Intake-Manifest über eine Umgebungsvariable `SV_ASSET_SOURCE`
  referenziert. Ins Repo kommen nur die verarbeiteten GLBs, die das Spiel
  nutzt. Grund: Pakete sind groß; Git soll Spiel und Pipeline versionieren,
  nicht Bibliotheken.
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

## 8. Projektstruktur ⚠

Empfehlung: Godot-Projekt unter **`game/`** (Godot 4.6). `art/`, `build/`
und `docs/` liegen damit außerhalb von `res://` und werden nicht importiert.
Verarbeitete Assets: `game/assets/{characters,crops,nature,props,buildings}/`.

## 9. Meilenstein 1: kleine Garten-Szene

Ziel: **Player, ein arbeitendes Naturwesen, ein wachsendes Beet** in einer
Godot-Szene, auf dem Handy abgenommen. Beantwortet, ob die Assets den Charme
der Referenz erreichen und welche Player-Variante trägt.

Sessions sind einzeln ausführbar. **Ausführung:** *Claude* = Claude Code;
*DeepSeek* = DeepSeek V4.1 Flash in OpenCode (gleicher Repo-Zugriff). Pro
Datei ein Schreiber; parallele Sessions nur bei getrennten Schreibbereichen.
Alle Sessions: Branch `claude/wurzelheim-env-audit-tmlfav`, Handoff nach
AGENTS.md, `docs/STATUS.md` aktualisieren.

| # | Session | Ausführung | Abhängig von |
|---|---|---|---|
| S0 | Pakete herunterladen und ablegen | Nutzer, manuell | – |
| S1 | Godot-Projekt-Grundgerüst | DeepSeek · medium | – |
| S2 | Intake-Skript und Herkunftsnachweis | DeepSeek · medium, Review Claude · low | S0, S1 |
| S3 | Lineup und Player-Entscheidung | Claude · high | S2 |
| S4 | Garten-Szene in Godot | DeepSeek · medium, Sichtprüfung Claude · medium | S1, S2, S3 |
| S5 | Gemeinsamer Wesen-Grundkörper + Waldwesen | Claude · high | S3 |
| S6 | Prozedurale Animationen | DeepSeek · medium, Sichtprüfung Claude · low | S4, S5 |
| S7 | Icon-Renderer | DeepSeek · low | S2 |

### S0 – Pakete ablegen (Nutzer)

Herunterladen: Stylized Nature MegaKit, Ultimate Crops, Fantasy Props MegaKit,
Farm Buildings, Ultimate Monsters (von quaternius.com, jeweils die kostenlose
Edition, sofern nicht anders entschieden). Entpacken nach
`D:\Mika\assets\quaternius\<paket>\<version-oder-datum>\`, Lizenzdatei bzw.
Screenshot der Lizenzangabe daneben. Umgebungsvariable
`SV_ASSET_SOURCE=D:\Mika\assets` setzen. Ergebnis: Liste der Ordner mit
Edition und Datum an die nächste Session geben.

### S1 – Godot-Grundgerüst (DeepSeek · medium)

- **Ist:** Kein Godot-Projekt im Repo. Godot 4.6:
  `D:\Mika\tools\godot\Godot_v4.6-stable_win64.exe`. `.gitignore` ignoriert
  `/build/`. Konventionen: Abschnitt 2 und 7.
- **Aufgabe:** `game/project.godot` (Name „Spirit Village“, Hochformat
  360 × 800, Stretch-Modus `canvas_items`, Aspekt `expand`, Renderer Mobile),
  Ordner `game/assets/{characters,crops,nature,props,buildings}/`,
  `game/scenes/`, `game/scripts/`. `game/.godot/` in `.gitignore`;
  `*.import`-Dateien werden nach Godot-Konvention versioniert. Leere Hauptszene
  `game/scenes/garden.tscn` mit orthografischer `Camera3D` (50° nach unten),
  `DirectionalLight3D` (warm, Schatten an) und `WorldEnvironment` (helle,
  warme Umgebung).
- **Abnahme:** `Godot --headless --path game --import` endet ohne Fehler;
  `Godot --headless --path game --quit` startet die Hauptszene ohne Fehler.
  Ausgaben als Beleg.
- **Schreibbereich:** `game/`, `.gitignore`, `docs/STATUS.md`.

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

- **Ist:** Intake-GLBs unter `game/assets/`; Varianten A/B/C (Abschnitt 4).
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
  aufbauen: Wege, 3 × 3-Beet, 3 Bäume, 1 Haus, 1 Station, Player an fester
  Position, 1 Helfer. Pflanzen wechseln per Skript
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

## 10. Offene Entscheidungen

1. Player-Variante A/B/C (S3; Empfehlung A).
2. Rohdownloads außerhalb von Git unter `D:\Mika\assets` (Empfehlung: ja).
3. Godot-Projekt unter `game/` (Empfehlung: ja).
4. Kostenlose oder kostenpflichtige Paketeditionen (Empfehlung: erst kostenlos,
   nach der Lineup-Abnahme gezielt ergänzen).
