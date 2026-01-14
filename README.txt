Mit dem Plugin Treesta Importer kannst du deine alten Baumkataster-Daten (aus Baumsicht) in das neue Treesta-Format umwandeln – direkt in QGIS.

1. ✅ Was du brauchst

Eine CSV-Datei mit deinen alten Baumdaten

Die im Plugin enthaltenen Dateien:

fields_mapping.csv

value_mapping.csv
Diese sind bereits im Plugin enthalten – du musst hier nichts anpassen (außer du willst eigene Zuordnungen ergänzen).

2. 📤 So exportierst du deine alten Daten (z. B. aus Baumsicht)

In QGIS:

Wähle deinen alten Baumlayer aus

Rechtsklick → „Exportieren“ → „Objekte speichern als…“

Wähle oben „Komma-getrennte Werte [CSV]“

Achte auf folgende Einstellungen (u.a. in den Layeroptionen):

EinstellungWertSEPARATORSEMICOLONGEOMETRYAS_WKT (empfohlen)DATEINAMEz. B. altes_kataster.csv

📌 Wichtig: Speichere die Datei an einem einfachen Pfad ohne Sonderzeichen.

3. 🚀 So verwendest du das Plugin

Installation über Erweiterungen → Erweiterungen verwalten und installieren.

Starte QGIS und öffne ein beliebiges Projekt

Gehe auf Erweiterung→ Treesta Importer

Klicke auf „Durchsuchen…“ und wähle deine exportierte altes_kataster.csv

Klicke auf „Umwandlung starten“

Das Plugin erzeugt:

eine umgewandelte Datei: treesta_import.csv (im gleichen Ordner)

eine Textdatei mit nicht gemappten Werten: unmapped_values.txt
→ diese Datei zeigt dir, welche Begriffe nicht automatisch übersetzt werden konnten

4. 📥 Import in Treesta

Öffne deine Datenbank von Treesta in QGIS (nicht das Projekt, nur die Datenbank laden). Vorher Daten sichern!

Um die Datei zu laden, ziehe die Datei nicht per Drag & Drop in QGIS! Dadurch werden alle Spalten als Text behandelt, was zu Fehlern beim Einfügen führt.

Richtiges Vorgehen:

Klicke in QGIS auf Layer → „Datenquellenverwaltung“ (Tastenkürzel: Strg+L)

Wähle links „Getrennte Texte“

Wähle die Datei treesta_import.csv

Stelle sicher:
Trennzeichen: Semikolon

Anführungszeichen: "

Geometrie: Well-Known-Text (WKT)

KBS: EPSG:4326 - WGS 84

QGIS erkennt die Spalten automatisch

Jetzt in den Ziel-Layer:

Aktiviere Bearbeitungsmodus des Layer Trees

Füge die Daten ein (Strg+V)

Speichere die Layeränderung


ℹ️ Hinweis zu weiteren Daten

Aktuell werden nur Baumdaten verarbeitet (Punkte mit Attributen).
Flächen, Linien sind noch nicht enthalten, werden aber zukünftig unterstützt.

🛠 Hinweis zum Plugin-Status
Das Treesta Importer Plugin befindet sich aktuell noch in der Anfangsphase.
Die Konvertierung deiner Baumdaten funktioniert bereits zuverlässig in den meisten Fällen – trotzdem solltest du die umgewandelten Daten nach dem Import unbedingt prüfen:

Sind alle Werte korrekt zugeordnet?

Wurden alle wichtigen Felder übernommen?

Gibt es sichtbare Fehler oder Auffälligkeiten?

🔍 Unser Tipp: Kontrolliere besonders Maßnahmen, Merkmale und Werte mit Sonderzeichen oder Kommas.

Bei Rückfragen oder Verbesserungswünschen freuen wir uns über Feedback!
