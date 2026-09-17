# Art Pipeline

Blender-Python-Generatoren für Spirit-Village-Figuren. Jeder Generator ist
ein eigenständiges, reproduzierbares Skript unter `art/generators/`, das mit
Blender im Hintergrundmodus ausgeführt wird und `.blend`-Quelldateien sowie
`.glb`-Exporte für Godot erzeugt. Keine Add-ons, keine externen
Python-Pakete, keine heruntergeladenen Assets.

Arbeitsweise (Daten-API statt Operatoren, visuelle Feedbackschleife,
Prüfungen): **[BLENDER_WORKFLOW.md](BLENDER_WORKFLOW.md)**.

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
  kein Metallic), keine Texturen.
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

Jeder Lauf prüft außerdem Durchdringungen zwischen Teilen, die sich nicht
berühren dürfen (`SEPARATE_PARTS`, BVH-Overlap der Meshes), und meldet
`WARNING intersection: …` sowie eine Zusammenfassung. Der Lauf bricht dabei
nicht ab.

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

### Stand und Prüfungen

**Bildhöhe vs. Figurenhöhe:** Die Vorschau ist 1024 px hoch, die Figur nimmt
darin 553 px ein (vom Generator ausgegeben). Kleinprüfungen beziehen sich auf
die **Figurenhöhe**.

Ausgeführt mit dem Stand dieses Commits (Blender 5.2.1 LTS, Windows,
Nutzer-PC; Protokoll lokal unter `build/characters/garden_wight/run.log`):

- Generator mit `--views`: Exit 0; `.blend`, `.glb`, Vorschau und vier
  Prüfbilder erzeugt; gebaute Höhe 0,949, Sohlen auf z = 0;
  Durchdringungsprüfung 0 von 15 Paaren.
- Alle Bilder angesehen (Kopien unter `docs/previews/`):
  - Vorschau `garden_wight.png`: ganze Figur, Augen mit Glanzpunkt frei,
    Krempe mit Überhang, Gurt links neben dem Gesicht, kein Mund-Bogen,
    Füße sichtbar.
  - Rückansicht `garden_wight_back.png` und Beutelseite
    `garden_wight_side_bag.png`: durchgehende Gurtschlaufe über die Schulter,
    Enden in Klappe und Beutel, Hand frei vom Beutel, kein sichtbares
    Versinken.
  - `garden_wight_fig96px.png` (Figur 96 px): Augen samt Glanzpunkt, Kappe
    und Gurt erkennbar. `garden_wight_fig48px.png` (Figur 48 px): Augen und
    Kappe lesbar, der Gurt nur als schmaler Ockerstreifen.
- GLB-JSON: 14 Nodes, 13 Meshes, 7 Materialien, ca. 9 200 Dreiecke, keine
  Kameras/Lichter/Boden, keine Node-Skalierung; Augen bei glTF z = +0,255
  (Gesicht vorne +Z).
- Rechnerisch (Python ohne Blender): Mindestabstand der Riemen-Innenseite zur
  Körperoberfläche = `strap_lift`; alle Riemenabschnitte unterhalb der
  Beuteloberkante liegen samt Endbreite und Dicke im Beutelquader.
- Zwei Exporte derselben Revision verglichen: JSON und alle Positionen und
  Normalen identisch; bei den UV-Kugel-Meshes (Körper, Augen, Glanzpunkte,
  Füße, Hände)
  unterscheidet sich nur die **Reihenfolge** der Dreiecke, die Dreiecksmengen
  sind gleich. Vor-Triangulierung per `bmesh` behebt das nicht. Die Ursache
  liegt vermutlich im glTF-Exporter; keine sichtbaren Auswirkungen.

Ausstehend (NOT RUN): Godot-Import, andere Blender-Versionen.

Offene visuelle Befunde:

1. **48 px Figurenhöhe:** Der Gurt ist kaum als Gurt lesbar.
2. **Hände** wirken aus der 50°-Kamera noch leicht wie seitliche Ohren.
3. **Knick am Beutel:** Der Gurt biegt über der Klappe deutlich in den
   senkrechten Lauf.
