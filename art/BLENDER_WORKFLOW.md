# Blender-Workflow für Generatoren

Verbindliche Arbeitsweise für Blender-Python-Generatoren unter
`art/generators/`. Die Regeln stammen aus einem Leitfaden zur KI-gestützten
Blender-Automation und sind auf diesen Projektstand zugeschnitten. **Belegt**
heißt: in diesem Repository mit Blender 5.2.1 LTS ausgeführt. **Nicht
vorgesehen** heißt: bewusst nicht eingesetzt.

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

## 5. Blender MCP (interaktiv, Nutzer-PC)

Live-Verbindung eines Agenten zu einem **geöffneten** Blender: Szene abfragen,
Code ausführen, Screenshots. Einsatz: schnelles Ausprobieren und Feintuning,
während der Nutzer zusieht. **Ergebnisse zählen erst, wenn sie in die `CONFIG`
bzw. den Code eines Generators übertragen und mit einem Hintergrundlauf
(`--views`) bestätigt sind.** Der Generator bleibt die Quelle der Wahrheit.

**Eingerichtet** (Nutzer-PC, 2026-09-17, mit Blender 5.2.1 geprüft):

- Paket `mcp-for-blender` **2.0.0** (MIT, github.com/ahujasid/blender-mcp;
  früher `blender-mcp`), Addon „MCP for Blender“ 1.7. Der Quelltext des Addons
  wurde vor der Installation durchgesehen; die installierte Datei ist
  bytegleich.
- Addon-Datei einmal pro Blender-Version:
  `uvx mcp-for-blender@2.0.0 install-addon` →
  `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`.
- Claude Code, nur lokal für dieses Projekt (nicht im Repo):
  `claude mcp add --scope local blender --env DISABLE_TELEMETRY=true -- uvx mcp-for-blender@2.0.0`.
  Die Werkzeuge erscheinen erst in einer **neuen** Claude-Code-Sitzung.
- Blender-Sitzung starten (GUI, nicht `--background`):

  ```bash
  "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" \
    --python art/tools/blender_mcp_session.py [-- pfad/zur/datei.blend]
  ```

  Das Skript aktiviert das Addon **nur für diese Sitzung** (kein Eintrag in den
  Einstellungen). Der Server startet automatisch auf `127.0.0.1:9876`.

**Sicherheits- und Datenschutzregeln:**

- **Telemetrie aus.** Standardmäßig wäre sie an und umfasst Prompts, Code,
  Screenshots und Bearbeitungsverläufe (laut Bedingungen auch für KI-Training).
  Abgeschaltet doppelt: `DISABLE_TELEMETRY=true` am MCP-Server und
  Addon-Zustimmung aus (geprüft: `get_telemetry_consent` → `false`).
- **Addon nie dauerhaft aktivieren** (nicht in den Einstellungen speichern):
  Es öffnet einen Socket ohne Authentifizierung, der beliebigen Python-Code
  ausführt. Geprüft: Nach dem Schließen ist der Port zu, kein
  Einstellungseintrag.
- Vor MCP-Arbeit offene Dateien speichern; MCP bevorzugt auf Kopien oder
  Generator-Ausgaben unter `build/` anwenden.
- **Externe Dienste im Addon bleiben aus** (Poly Haven, Sketchfab, Poly Pizza,
  Hyper3D, Hunyuan3D). Assets kommen nur über die dokumentierte Intake-Pipeline
  mit Herkunftsnachweis (siehe [PIPELINE.md](PIPELINE.md)).
- Version gepinnt; ein Update erst nach erneuter Quelltextdurchsicht.

## 6. Nicht vorgesehen

- **BlenderProc** (synthetische Trainingsdaten, Masken, Tiefenkarten): für
  handgestaltete Spielassets ohne Nutzen.
- **`fake-bpy-module`** (Typ-Stubs für Editor-Autovervollständigung):
  optional für die lokale Entwicklung; ersetzt keinen echten Blender-Lauf.
