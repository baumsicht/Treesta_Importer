Treesta Importer – Anleitung

Download: über GitHub oder direkt in QGIS über Erweiterungen → Erweiterungen verwalten und installieren.

Mit dem Plugin Treesta Importer kannst du Daten aus Baumkataster 3 und 4 in das neue Treesta-Format umwandeln – direkt in QGIS.

Unterstützt werden:

permanente Bäume

temporäre Einzelbäume

Flächen

Pläne

Die verschiedenen Layer werden jeweils einzeln exportiert, konvertiert und anschließend in den entsprechenden Treesta-Layer eingefügt.

1. ✅ Was du brauchst

Du benötigst eine oder mehrere CSV-Dateien mit deinen bisherigen Daten. Exportiere jeden vorhandenen Layer separat.

Die erforderlichen Zuordnungsdateien sind bereits im Plugin enthalten:

fields_mapping*.csv

value_mapping*.csv

Du musst daran nichts ändern. Nur für eigene oder abweichende Zuordnungen können die Dateien bei Bedarf erweitert werden.

2. 📤 Daten aus dem bisherigen Baumkataster exportieren

Wiederhole den Export für jeden Layer, den du nach Treesta übernehmen möchtest:

Bäume

temporäre Einzelbäume

Flächen

Pläne

Export in QGIS

Wähle den gewünschten Layer aus.

Klicke mit der rechten Maustaste auf den Layer.

Wähle Exportieren → Objekte speichern als …

Wähle als Format Komma-getrennte Werte [CSV].

Verwende folgende Einstellungen:

EinstellungWertFormatKomma-getrennte Werte [CSV]KodierungUTF-8TrennzeichenSemikolonGeometrieAS_WKTKBSmöglichst EPSG:4326 – WGS 84Dateinamez. B. alte_baeume.csv

Die Geometrie muss als Well-Known Text (WKT) ausgegeben werden. Das gilt sowohl für Punkte als auch für Polygone.

3. 🚀 Daten mit dem Plugin umwandeln

Installiere das Plugin über Erweiterungen → Erweiterungen verwalten und installieren.

Öffne in QGIS ein beliebiges Projekt.

Starte den Treesta Importer.

Klicke auf Durchsuchen … und wähle die zuvor exportierte CSV-Datei.

Wähle im Dropdown den passenden Datentyp:

Permanente Bäume

Temporäre Bäume

Fläche

Plan

Klicke auf Umwandlung starten.

Wiederhole die Umwandlung für jeden exportierten Layer.

Erzeugte Importdateien

Je nach ausgewähltem Datentyp erzeugt das Plugin im Ordner der Ausgangsdatei eine eindeutig benannte CSV-Datei:

Auswahl im PluginErzeugte DateiZiellayer in TreestaPermanente Bäumebäume-treesta-import.csvBäumeTemporäre Bäumeeinzelbäume-treesta-import.csvBäumeFlächeflächen-treesta-import.csvFlächenPlanpläne-treesta-import.csvFlächen

Zusätzlich kann das Plugin folgende Datei erzeugen:

unmapped_values.txt

Darin stehen Werte, die nicht automatisch zugeordnet werden konnten. Prüfe diese Datei nach jeder Umwandlung, bevor du den nächsten Layer konvertierst.

Der Importer setzt außerdem automatisch die erforderlichen Kennwerte:

permanente Bäume: temp = 0

temporäre Bäume: temp = 1

Flächen: documentation = 1 und atlas = 0

Pläne: atlas = 1

4. 📥 Daten in Treesta importieren

Treesta-Datenbank laden

Erstelle vor dem Import eine Sicherung der Treesta-Datenbank, insbesondere wenn sie bereits Daten enthält.

Öffne QGIS.

Lade nur die Treesta-Datenbank database.gpkg, nicht das vollständige Treesta-Projekt.

Ziehe dazu database.gpkg in QGIS und wähle die benötigten Ziellayer aus.

Wichtig: CSV nicht per Drag-and-drop laden

Ziehe die erzeugte CSV-Datei nicht einfach in QGIS. Dabei können sämtliche Spalten als Text erkannt werden, was beim Einfügen in die Treesta-Datenbank zu Fehlern führen kann.

CSV richtig laden

Öffne Layer → Datenquellenverwaltung.

Wähle links Getrennte Texte.

Wähle die passende Importdatei, beispielsweise flächen-treesta-import.csv.

Stelle Folgendes ein:

EinstellungWertTrennzeichenSemikolonAnführungszeichen"GeometrieWell-Known Text (WKT)Geometriefelddas Feld mit der WKT-GeometrieKBSEPSG:4326 – WGS 84 oder das beim Export verwendete KBS

QGIS erkennt die weiteren Spalten normalerweise automatisch.

Objekte in den Treesta-Layer kopieren

Öffne die Attributtabelle der geladenen CSV.

Wähle die gewünschten Objekte aus:

alle auswählen mit Strg+A

kopieren mit Strg+C

Aktiviere beim entsprechenden Treesta-Ziellayer den Bearbeitungsmodus.

Füge die Daten mit Strg+V ein.

Speichere die Layeränderungen.

Achte darauf, dass die Daten in den richtigen Layer eingefügt werden:

bäume-treesta-import.csv → tree_data

einzelbäume-treesta-import.csv → tree_data

flächen-treesta-import.csv → polygons

pläne-treesta-import.csv → polygons

5. 🔍 Import prüfen

Kontrolliere die Daten nach jedem Import:

Sind Anzahl und Positionen der Objekte korrekt?

Wurden Punkt- und Polygongeometrien richtig übernommen?

Stimmen Baumarten, Maßnahmen und Dringlichkeiten?

Sind Flächen und Pläne richtig symbolisiert?

Wurden Datumsfelder übernommen?

Sind Fotoangaben und Dateipfade vorhanden?

Gibt es nicht zugeordnete Werte in unmapped_values.txt?

Sind Sonderzeichen, Umlaute und Werte mit Kommas korrekt?

Fotofelder und darin gespeicherte Dateinamen oder Pfade werden übernommen. Die eigentlichen Bilddateien müssen jedoch ebenfalls in den vorgesehenen Fotoordner übertragen werden.

Videoanleitung

Treesta Importer auf YouTube

🛠 Hinweis zum Plugin-Status

Die Konvertierung aus Baumkataster 4 wurde um permanente und temporäre Bäume, Flächen und Pläne erweitert.

Der Import aus Baumkataster 3 ist grundsätzlich vorhanden. Die neuen Funktionen für die verschiedenen Layer werden hierfür noch gesondert geprüft. Kontrolliere umgewandelte Daten deshalb grundsätzlich sorgfältig, bevor du mit der Treesta-Datenbank weiterarbeitest.