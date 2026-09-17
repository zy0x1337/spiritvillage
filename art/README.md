# Art Pipeline

Blender-Python-Generatoren für Spirit-Village-Figuren. Jeder Generator ist
ein eigenständiges, reproduzierbares Skript unter `art/generators/`, das mit
Blender im Hintergrundmodus ausgeführt wird und `.blend`-Quelldateien sowie
`.glb`-Exporte für Godot erzeugt. Keine Add-ons, keine externen
Python-Pakete, keine heruntergeladenen Assets.

## garden_wight.py — Gartenwicht (Player-Charakter)

Erste statische Version des nichtmenschlichen Spielercharakters: ein
gedrungener, birnenförmiger Gartenwicht.

### Konventionen

- **Z-up**, beide Fußsohlen exakt auf `z = 0`, Gesamthöhe ca. 1 Blender-Einheit.
- **Blickrichtung −Y.** Blenders Frontansicht (Numpad 1) schaut von −Y nach
  +Y und zeigt damit das Gesicht; nach der glTF-Y-up-Konvertierung
  entspricht −Y der −Z-Vorwärtsachse, die Godot erwartet. Augen, Riemen und
  Vorschaukamera verwenden dieselbe Vorderseite (`FRONT_SIGN`).
- **Alle `CONFIG`-Maße sind volle Ausdehnungen** (Durchmesser, Länge,
  Breite, Höhe) — nie Radien. Primitives werden in Einheitsgröße erzeugt und
  auf diese Maße skaliert, `body_width` ist also wirklich der größte
  Durchmesser des fertigen Körpers.
- Verhältniswerte (`*_ratio`) sind Anteile von `body_height`, gemessen ab dem
  tiefsten Punkt des Körpers.

### Gestaltung

- **Körper/Kopf**: ein einziges, parametrisch verformtes Mesh (Kugel →
  Birnenform über eine radiale Profilfunktion). Die Profilfunktion wird
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
- **Hände**: zwei kurze, abgerundete Stubs ohne Finger, an der Flanke
  eingebettet und leicht nach außen geneigt.
- **Augen**: zwei dunkle Kugeln auf dem Rotationsquerschnitt der Kopfhöhe,
  um `eye_protrusion` nach außen versetzt, deutlich unterhalb der
  Kappenkrempe.
- **Kappe**: Kegel, dessen Mesh so verschoben ist, dass der Objektursprung
  auf der Krempe liegt — `cap_lean_deg` kippt die Kappe damit um ihre Basis.
  Ein `Simple Deform`-Modifier (Bend, nur oberer Bereich) knickt die Spitze um.
- **Samenbeutel & Riemen**: abgerundeter Quader an der Flanke gegenüber der
  Kappenneigung; der Riemen ist ein schmales Band, dessen Endpunkte rechnerisch
  auf Schulterpunkt und Beuteloberkante liegen.
- **Materialien**: flache, matte Principled-BSDF-Materialien (hohe Rauheit,
  kein Metallic), keine Texturen.

Alle Maße, Positionen und Farben stehen zentral im `CONFIG`-Dict am
Skriptanfang; `derive_dimensions()` löst daraus alle konkreten
Weltkoordinaten auf.

### Annahmen / API-Ziel

- **Blender 4.5 LTS** als vorläufige API-Basis. Die tatsächlich installierte
  Version ist noch nicht bestätigt — vor dem ersten echten Lauf
  `bpy.app.version` prüfen und bei Abweichung die API-Aufrufe kontrollieren
  (insbesondere `bmesh.ops.create_uvsphere`, die `export_scene.gltf`-Parameter
  und den Node-Namen `"Principled BSDF"`).
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
# Pfad zur Blender-Programmdatei ggf. anpassen — je nach Installation ist der
# vollständige Pfad nötig, z. B. auf macOS
# /Applications/Blender.app/Contents/MacOS/Blender oder unter Windows
# "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

blender --background --factory-startup --python \
  art/generators/garden_wight.py -- \
  --output-dir build/characters/garden_wight --render
```

- `--output-dir <pfad>`: Zielverzeichnis (relative Pfade werden gegen das
  Arbeitsverzeichnis aufgelöst, aus dem Blender gestartet wurde). Standard:
  `build/characters/garden_wight`.
- `--render` (optional): erzeugt zusätzlich die PNG-Vorschau.

Erzeugte Dateien:

- `garden_wight.blend` — Charakter-Collection `GardenWight_Character` **und**
  Vorschau-Setup `GardenWight_PreviewSetup` (Boden, Sonne, orthografische
  Kamera).
- `garden_wight.glb` — **ausschließlich** die Figur inklusive Materialien.
  Der Export läuft, bevor das Vorschau-Setup überhaupt existiert, es können
  also weder Kamera noch Licht noch Boden hineingeraten.
- `garden_wight_preview.png` (nur mit `--render`).

### Vorschaukamera und Renderweg

Die Kamera wird aus den abgeleiteten Figurmaßen berechnet, nicht von Hand
gesetzt: Sie steht auf der Vorderseite (−Y), blickt `preview_pitch_deg`
(50°) unter dem Horizont genau auf die Figurmitte, und `ortho_scale` ergibt
sich aus der projizierten Höhe und Breite der Figur plus `preview_margin`.
Höhen- und Breitenbedarf werden dabei gegen das Hochformat-Seitenverhältnis
geprüft, damit die komplette Figur im Bild bleibt.

`configure_render()` setzt **Cycles mit `device = 'CPU'`** und wird
**vor** `save_as_mainfile()` aufgerufen. Die gespeicherte `.blend` und ein
eventuelles `--render`-PNG verwenden dadurch identische Einstellungen.
Begründung für CPU: die Pipeline setzt nirgends eine konfigurierte GPU
voraus; Cycles-CPU ist über Blender-4.x-Installationen hinweg der
portabelste Weg zu einem Standbild. Auf einer GPU-Maschine kann
`scene.cycles.device` bei Bedarf umgestellt werden — bewusst keine
Automatik.

### Bekannter Stand: ungeprüft in Blender

Das Skript wurde bisher **nur ohne Blender geprüft**: Python-Syntax,
Argument-/Pfadlogik und die reinen Geometrieberechnungen
(`derive_dimensions`, Maßnormierung, Anbauteil-Platzierung, Kamerarahmung).
Ein tatsächlicher Blender-Lauf hat **nicht** stattgefunden — Mesh-Erzeugung,
Modifier-Ergebnisse, GLB-Export, `.blend`-Speicherung und Rendering sind
unbestätigt.

Beim ersten echten Render visuell beurteilen:

1. **Faltrichtung der Kappenspitze.** Der Bend-Modifier arbeitet um die
   X-Achse; ob die Spitze nach vorne (−Y, sichtbar) oder nach hinten knickt,
   hängt vom Vorzeichen ab. Notfalls `cap_bend_deg` negieren.
2. **Riemenband am Brustkorb.** Das Band ist eine gerade Box zwischen zwei
   exakt berechneten Endpunkten; auf der gewölbten Brust dazwischen kann es
   teilweise eintauchen. Falls es verschwindet, `strap_depth` oder
   `strap_y` anpassen.
3. **Silhouette und Lesbarkeit bei kleiner Darstellung** — Verhältnis von
   Körperbreite, Kappenkrempe und Augengröße aus der 50°-Kamera.
