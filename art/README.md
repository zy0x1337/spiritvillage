# Art Pipeline

Blender-Python-Generatoren für Spirit-Village-Figuren. Jeder Generator ist
ein eigenständiges, reproduzierbares Skript unter `art/generators/`, das mit
Blender im Hintergrundmodus ausgeführt wird und `.blend`-Quelldateien sowie
`.glb`-Exporte für Godot erzeugt. Keine Add-ons, keine externen
Python-Pakete, keine heruntergeladenen Assets.

## garden_wight.py — Gartenwicht (Player-Charakter)

Erste statische Version des nichtmenschlichen Spielercharakters: ein
gedrungener, birnenförmiger Gartenwicht.

### Gestaltung

- **Körper/Kopf**: ein einziges, parametrisch verformtes Mesh (Kugel →
  Birnenform über eine radiale Profilfunktion entlang der Höhe). Kopf und
  Rumpf gehen bewusst ohne Nahtstelle ineinander über. Dieses Mesh dient
  gleichzeitig als sichtbarer cremefarbener Überwurf — für die erste
  statische Version gibt es keine separate Kleidungsgeometrie.
- **Hände**: zwei kurze, abgerundete Kugel-Stubs ohne einzelne Finger, leicht
  nach außen/unten geneigt (entspannte Pose).
- **Füße**: zwei kleine, dunkelbraune, abgeflachte Kugeln auf Bodenhöhe 0.
- **Augen**: zwei kleine dunkle Kugeln, an der Vorderseite des oberen
  Körperbereichs platziert (unterhalb der Kappenbasis), damit sie aus der
  schrägen Top-Down-Kamera sichtbar bleiben.
- **Kappe**: ein Kegel mit einem `Simple Deform`-Modifier (Bend, nur oberer
  Bereich), der die Spitze umknickt, plus einer leichten Rotation für die
  geforderte Asymmetrie.
- **Samenbeutel & Riemen**: ein abgerundeter Quader (Bevel-Modifier) an der
  Hüfte, gegenüber der Kappen-Neigung positioniert, mit einem schmalen
  diagonalen Riemen zur gegenüberliegenden Schulter.
- **Materialien**: flache, matte Principled-BSDF-Materialien (hohe
  Rauheit, kein Metallic), keine Texturen — cremeweiß, moosgrün,
  dunkelbraun, dunkles Augenschwarz, Ocker (hell/dunkel für Beutel/Riemen).

Alle Maße, Positionen und Farben stehen zentral im `CONFIG`-Dict am
Skriptanfang und sind dort dokumentiert.

### Annahmen / API-Ziel

- **Blender 4.5 LTS** als vorläufige API-Basis. Die tatsächlich auf dem
  Zielrechner installierte Version ist noch nicht bestätigt — vor dem ersten
  echten Lauf `bpy.app.version` prüfen und bei Abweichungen die
  API-Aufrufe (insbesondere `bmesh.ops.create_uvsphere`,
  `export_scene.gltf`-Parameter, Node-Namen wie `"Principled BSDF"`) im
  Skript kontrollieren.
- Das Skript geht von einer **leeren Factory-Startup-Szene** aus und räumt
  am Anfang (`clear_scene()`) rigoros alles vorhandene aus der Szene.
  Deshalb **nur** in einem eigenen Hintergrundprozess ausführen, niemals in
  einer geöffneten Arbeitsdatei.

### Verwendung

Argumente werden **nach** `--` gelesen (Blender-Konvention).

```bash
# Pfad zur Blender-Programmdatei ggf. anpassen — je nach Installation kann
# der vollständige Pfad nötig sein, z. B. auf macOS
# /Applications/Blender.app/Contents/MacOS/Blender oder unter Windows
# C:\Program Files\Blender Foundation\Blender 4.5\blender.exe

blender --background --factory-startup --python \
  art/generators/garden_wight.py -- \
  --output-dir build/characters/garden_wight --render
```

- `--output-dir <pfad>`: Zielverzeichnis für die Ausgabedateien (relative
  Pfade werden gegen das Arbeitsverzeichnis aufgelöst, aus dem Blender
  gestartet wurde). Standard: `build/characters/garden_wight`.
- `--render` (optional): erzeugt zusätzlich eine PNG-Vorschau.

Erzeugte Dateien in `--output-dir`:

- `garden_wight.blend` — enthält die Charakter-Collection
  (`GardenWight_Character`) **und** ein zusätzliches Vorschau-Setup
  (`GardenWight_PreviewSetup`: Boden, Sonne, orthografische Kamera).
- `garden_wight.glb` — enthält **ausschließlich** die Figur inklusive
  Materialien (keine Kamera, kein Licht, kein Boden).
- `garden_wight_preview.png` (nur mit `--render`) — orthografische
  Vorschau, Kamera ca. 50° nach unten geneigt, komplette Figur, neutraler
  Boden, weiches Sonnenlicht.

### Renderweg für die Vorschau

`--render` verwendet **Cycles mit `device = 'CPU'`**. Begründung: das
Skript soll auch auf Maschinen ohne garantierte/konfigurierte GPU
(z. B. Headless-CI) einen Stand-Render erzeugen können; Cycles-CPU ist über
Blender-4.x-Installationen hinweg der portabelste Weg zu einem stillen
Bild. Steht auf dem Zielrechner eine GPU zur Verfügung, kann
`scene.cycles.device` im Skript bei Bedarf auf `'GPU'` (mit passendem
`compute_device_type`, z. B. OPTIX/CUDA/HIP) umgestellt werden, um die
Iteration zu beschleunigen — aktuell bewusst nicht automatisch erkannt.

### Bekannter Stand: noch ungeprüft

Dieses Skript wurde bislang **nur auf Python-Syntax und Argument-/
Pfadlogik geprüft** (siehe Commit-Historie / Abschlussbericht), **nicht**
tatsächlich in Blender ausgeführt. Insbesondere folgende Punkte sind bis
zum ersten echten Lauf offen und sollten dann visuell beurteilt werden:

1. Wirkt die Birnenform von Körper/Kopf aus der schrägen Top-Down-Kamera
   stimmig, oder muss `body_width`/`body_height`/die Profilfunktion
   nachjustiert werden?
2. Verdeckt die Kappe die Augen bei der Zielkamera-Neigung (~50°)
   tatsächlich nicht?
3. Wirkt der gerade, diagonale Riemen auf der gekrümmten Körperoberfläche
   plausibel, oder braucht er eine gebogene Geometrie?

Weitere, nicht in dieser Liste enthaltene technische Schritte (GLB-Import
in Godot, tatsächliche Blender-API-Kompatibilität, Render-Performance) sind
ebenfalls ungeprüft und Teil eines Folgeauftrags.
