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
- **Blickrichtung −Y** in Blender. Blenders Frontansicht (Numpad 1) schaut
  von −Y nach +Y und zeigt das Gesicht. Augen, Riemen und Vorschaukamera
  verwenden dieselbe Vorderseite (`FRONT_SIGN`).
- **Im GLB zeigt das Gesicht nach glTF +Z** — geprüft in der exportierten
  Datei (Augen-Nodes bei z = +0,255). Das ist die glTF-Vorderseitenkonvention
  und entspricht in Godot `Vector3.MODEL_FRONT` (+Z), **nicht** der
  −Z-Vorwärtsrichtung von `Node3D`/`look_at()`. In Godot also
  `look_at(ziel, Vector3.UP, true)` verwenden oder das Modell um 180° drehen.
  Der Godot-Import selbst ist noch nicht ausgeführt.
- **`.L`/`.R`** folgen Blenders Spiegelkonvention: linke Körperseite der
  Figur = +X.
- **Alle `CONFIG`-Maße sind volle Ausdehnungen** (Durchmesser, Länge,
  Breite, Höhe) — nie Radien. Primitives werden in Einheitsgröße erzeugt und
  auf diese Maße skaliert, `body_width` ist also wirklich der größte
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
  eingebettet; die unteren Enden spreizen leicht nach außen (hängende
  Haltung).
- **Augen**: zwei dunkle Kugeln auf dem Rotationsquerschnitt der Kopfhöhe,
  um `eye_protrusion` nach außen versetzt, deutlich unterhalb der
  Kappenkrempe.
- **Kappe**: per bmesh direkt erzeugter Kegel entlang einer gekrümmten
  Mittellinie: gerade bis `cap_bend_start`, danach biegt sich die Spitze um
  `cap_bend_deg` zur Neigungsseite (+X). Kein Modifier. Objektursprung auf der
  Krempenmitte, `cap_lean_deg` kippt die Kappe um ihre Basis; Unterseite
  geschlossen.
- **Samenbeutel & Riemen**: abgerundeter Quader an der Flanke gegenüber der
  Kappenneigung. Der Riemen ist ein geschlossenes Band, das `strap_path()` auf
  der Körperoberfläche folgt (plus `strap_lift`), vom Schulterpunkt an der
  Silhouette unterhalb der Augen bis zur Beuteloberkante.
- **Materialien**: flache, matte Principled-BSDF-Materialien (hohe Rauheit,
  kein Metallic), keine Texturen.

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

Erzeugte Dateien:

- `garden_wight.blend` — Charakter-Collection `GardenWight_Character` **und**
  Vorschau-Setup `GardenWight_PreviewSetup` (Boden, Sonne, orthografische
  Kamera).
- `garden_wight.glb` — **ausschließlich** die Figur inklusive Materialien.
  Der Export läuft, bevor das Vorschau-Setup überhaupt existiert. Geprüft:
  11 Nodes (`GardenWight_Root` + 10 Mesh-Teile, Mesh-Namen = Objektnamen),
  6 Materialien, keine Kameras, Lichter oder Boden.
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
voraus; Cycles-CPU ist über Blender-Installationen hinweg der
portabelste Weg zu einem Standbild. Auf einer GPU-Maschine kann
`scene.cycles.device` bei Bedarf umgestellt werden — bewusst keine
Automatik.

### Stand: erster Blender-Lauf

Geprüft mit Blender 5.2.1 LTS: Prozess Exit 0, `.blend`, `.glb` und PNG
erzeugt, gebaute Höhe 0,942 (Sohlen auf z = 0). Referenzvorschau:
`docs/previews/garden_wight.png`.

Beim ersten Lauf behoben: rautenförmiger Körper mit spitzem Boden
(Profilfunktion), verdrehte, schwebende Kappe (der Bend-Modifier bog quer zur
Kegelachse), im Brustkorb versunkener Riemen (Box → Oberflächenband), in der
Vorschau verdeckte Füße, ohrenartig abstehende Hände, vertauschte
`.L`/`.R`-Namen.

Offene visuelle Befunde:

1. **Riemen als Bogen.** Aus der 50°-Kamera wölbt sich das Band über den
   runden Bauch und kann bei kleiner Darstellung wie ein Mund wirken.
2. **Kleine Darstellung.** Bei ca. 96 px Bildhöhe sind Augen, Kappe und
   Riemen erkennbar; bei ca. 48 px bleiben nur weiße Form und grüne Kappe,
   die Augen sind kaum lesbar.
3. **Riemenende an der Schulter** endet offen an der Silhouette, statt über
   die Schulter nach hinten zu laufen; der Beutel ist ein schlichter Quader.
