Mit dem Plugin Treesta Importer kannst du deine alten Baumkataster-Daten aus dem Baumkataster 3 und 4 in das neue Treesta-Format umwandeln – direkt in QGIS.

1. ✅ Was du brauchst
Eine CSV-Datei mit deinen alten Baumdaten
Die im Plugin enthaltenen Dateien:
fields_mapping*.csv
value_mapping*.csv
Diese sind bereits im Plugin enthalten – du musst hier nichts anpassen (außer du willst eigene Zuordnungen ergänzen).
2. 📤 So exportierst du deine alten Daten (z. B. aus Baumsicht)
In QGIS:

Wähle deinen alten Baumlayer (Bäume) aus
Rechtsklick → „Exportieren“ → „Objekte speichern als…“
Wähle oben „Komma-getrennte Werte [CSV]“
Achte auf folgende Einstellungen (u.a. in den Layeroptionen):
Einstellung	Wert
Format	Komma-getrennte Werte [CSV]
Kodierung	UTF-8
SEPARATOR	SEMICOLON
GEOMETRY	AS_WKT (empfohlen)
DATEINAME	z. B. altes_kataster.csv

📌 Wichtig: Speichere die Datei an einem einfachen Pfad ohne Sonderzeichen.

3. 🚀 So verwendest du das Plugin

Installation über Erweiterungen → Erweiterungen verwalten und installieren.

Starte QGIS und öffne ein beliebiges Projekt
Gehe auf Erweiterung → Treesta Importer
Klicke auf „Durchsuchen…“ und wähle deine exportierte altes_kataster.csv
Klicke auf „Umwandlung starten“
Das Plugin erzeugt:

eine umgewandelte Datei: treesta_import.csv (im gleichen Ordner)
eine Textdatei mit nicht gemappten Werten: unmapped_values.txt
→ diese Datei zeigt dir, welche Begriffe nicht automatisch übersetzt werden konnten
4. 📥 Import in Treesta
Öffne deine Datenbank von Treesta in QGIS (nicht das Projekt, nur die Datenbank laden). Ziehe dazu database.gpkg in QGIS. Vorher ggf. Daten sichern, falls die Datenbank nicht leer ist!

Um die csv-Datei zu laden, ziehe die Datei nicht per Drag & Drop in QGIS! Dadurch werden eventuell alle Spalten als Text behandelt, was zu Fehlern beim Einfügen führen kann.

Richtiges Vorgehen:

Klicke in QGIS auf Layer → „Datenquellenverwaltung“ (Tastenkürzel: Strg+L)

Wähle links „Getrennte Texte“

Wähle die Datei treesta_import.csv

Stelle sicher:
Trennzeichen: Semikolon

Anführungszeichen: „

Geometrie: Well-Known-Text (WKT)

KBS: EPSG:4326 – WGS 84 (oder anderes, falls vorher eingestellt)

QGIS erkennt die Spalten automatisch

Wähle die gewünschten Objekte in der csv (alle mit Strg+A, Kopieren mit Strg+C oder im Menü)

Jetzt in den Ziel-Layer:

Aktiviere Bearbeitungsmodus des Layer Trees

Füge die Daten ein (Strg+V)

Speichere die Layeränderung
