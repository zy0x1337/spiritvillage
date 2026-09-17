# Blender-Workflow für Generatoren

Verbindliche Arbeitsweise für Blender-Python-Generatoren unter
`art/generators/`. Die Regeln stammen aus einem Leitfaden zur KI-gestützten
Blender-Automation und sind auf diesen Projektstand zugeschnitten. **Belegt**
heißt: in diesem Repository mit Blender 5.2.1 LTS ausgeführt. **Nicht
eingerichtet** heißt: beschrieben, aber hier weder installiert noch geprüft.

## 1. API-Regeln

- **`bpy.data` statt `bpy.ops` für Geometrie.** Meshes, Kameras, Lichter und
  Böden entstehen über `bpy.data.*.new()`, `bmesh` (`create_uvsphere`,
  `create_cube`, `bevel`, `scale`, `bm.to_mesh`) oder `mesh.from_pydata()`.
  Das hängt nicht vom UI-Kontext ab, braucht kein aktives Objekt und schlägt
  nicht an `poll()` fehl. *Belegt:* `garden_wight.py` erzeugt alle Teile so.
- **Operatoren nur, wo es keine Daten-API gibt:** glTF-Export, `.blend`
  speichern, Rendern. Im Hintergrundmodus brauchen diese drei keinen
  UI-Kontext. Braucht ein Operator doch einen (z. B. einen 3D-View), dann nur
  mit `with bpy.context.temp_override(...)`, nie mit globaler Auswahl- oder
  Kontextmanipulation.
- **Maße in die Mesh-Daten backen.** Keine nicht-uniforme Objektskalierung;
  Nodes im GLB tragen nur Position und Rotation. Das hält Normalen und
  Godot-Physik sauber.
- **Kein Modifier, dessen Ergebnis vom Export-Apply abhängt,** wenn dieselbe
  Form direkt gebaut werden kann (Erfahrung: ein Bend-Modifier bog die Kappe
  quer zur Achse).
- **Schattierung explizit:** `mesh.shade_smooth()` und bei Bedarf
  `mesh.set_sharp_from_angle(angle)` (Blender ≥ 4.1) für knackige Kanten an
  Taschen, Riemen und Krempen.
- **Versionen:** Die installierte Version prüfen (`bpy.app.version_string` wird
  bei jedem Lauf ausgegeben). Veraltete APIs versionsabhängig kapseln
  (Beispiel: `Material.use_nodes` nur vor 5.0).

## 2. Parametrischer Aufbau

- Alle Maße, Winkel, Farben und Mesh-Auflösungen stehen im `CONFIG`-Block am
  Skriptanfang, mit Einheit und Zweck im Kommentar. Werte sind volle
  Ausdehnungen, Verhältnisse beziehen sich auf eine dokumentierte Referenz.
- Reine Geometrieberechnung (`derive_dimensions`, Pfade, Profile) bleibt ohne
  `bpy` importierbar und lässt sich mit normalem Python prüfen.
- Anbauteile werden aus der tatsächlichen Oberfläche abgeleitet, nicht mit
  festen Koordinaten gesetzt.

## 3. Visuelle Feedbackschleife

Ein erfolgreicher Lauf ist kein Abnahmekriterium; erst die Bilder zählen.
Arbeitsweise in Rollen, die ein einzelner Agent nacheinander einnimmt:

1. **Planen:** Teile und Parameter benennen, Abnahmekriterien vorab festhalten.
2. **Coden:** parametrischer Generator nach Abschnitt 1 und 2.
3. **Kritisieren:** Mit `--views` rendern und **jedes Bild ansehen**:
   Vorschau (50°), Rückansicht, Beutelseite und Zuschnitte bei 96 und 48 px
   **Figurenhöhe**. Suchen nach schwebenden oder versunkenen Teilen, falschen
   Proportionen, Durchdringungen, Lesbarkeit bei kleiner Darstellung.
4. **Verifizieren:** Nach jeder Korrektur alle Ansichten erneut ansehen und
   die automatischen Prüfungen lesen: Durchdringungsprüfung (`SEPARATE_PARTS`,
   BVH-Overlap), gebaute Höhe, GLB-Inhalt. Eine Korrektur gilt erst, wenn sie
   keinen neuen Mangel erzeugt hat.

*Belegt:* So wurden beim Gartenwicht Kappe, Riemen, Hände und die
Hand-Beutel-Durchdringung gefunden – keiner dieser Fehler war an Exit-Code
oder Syntaxprüfung erkennbar.

Bild- und Figurenhöhe immer unterscheiden. Die Vorschau ist 1024 px hoch; die
Figur nimmt davon nur einen Teil ein (`--views` gibt den Wert aus).

## 4. Ausführung

```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background \
  --factory-startup --python-exit-code 1 --python art/generators/<generator>.py -- \
  --output-dir build/characters/<name> --views
```

- Immer `--factory-startup` in einem eigenen Prozess; Generatoren leeren die
  Szene.
- `--python-exit-code 1`, damit Python-Fehler den Prozess scheitern lassen.
- Ausgaben unter `build/` bleiben lokal; ausgewählte echte Renders dürfen nach
  `docs/previews/`.
- Handoff: ausgeführte Prüfungen mit Beleg, ausstehende als NOT RUN.

## 5. Nicht eingerichtet

- **Blender MCP** (Live-Verbindung zu einer laufenden Blender-Instanz über
  ein Addon und einen MCP-Server; Szene abfragen, Code direkt ausführen).
  Nutzen: schnellere, interaktive Iteration ohne Neustart pro Lauf und
  Feintuning, während der Nutzer zusieht. Grenzen: Das Addon führt beliebigen
  Code aus, der Server läuft in einem Hintergrund-Thread (Datenänderungen
  müssen im Hauptthread landen), und Ergebnisse sind nur reproduzierbar, wenn
  sie in die `CONFIG` des Generators zurückgeschrieben werden. Der Generator
  bleibt die Quelle der Wahrheit. Externe Dienste über MCP (Asset-Downloads,
  KI-Mesh-Generierung) widersprechen der Vorgabe „keine heruntergeladenen
  Assets“ und bräuchten eine eigene Entscheidung samt Herkunftsnachweis.
- **BlenderProc** (synthetische Trainingsdaten, Masken, Tiefenkarten): für
  handgestaltete Spielassets ohne Nutzen, daher nicht vorgesehen.
- **`fake-bpy-module`** (Typ-Stubs für Editor-Autovervollständigung):
  optional für die lokale Entwicklung; ersetzt keinen echten Blender-Lauf.
