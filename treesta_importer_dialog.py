# -*- coding: utf-8 -*-

import csv
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
)

from .converter_manager import smart_convert


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(
        os.path.dirname(__file__),
        "treesta_importer_dialog_base.ui"
    )
)


class TreestaImporterDialog(QDialog, FORM_CLASS):

    DATA_TYPES = (
        {
            "key": "permanent_trees",
            "label": "Permanente Bäume",
            "output_filename": "bäume-treesta-import.csv",
            "field_values": {"temp": "0"},
        },
        {
            "key": "temporary_trees",
            "label": "Temporäre Bäume",
            "output_filename": "einzelbäume-treesta-import.csv",
            "field_values": {"temp": "1"},
        },
        {
            "key": "area",
            "label": "Fläche",
            "output_filename": "flächen-treesta-import.csv",
            "field_values": {"documentation": "1"},
            "field_values": {"atlas": "0"},
            "field_renames": {"date": "last_modified_date"},
        },
        {
            "key": "plan",
            "label": "Plan",
            "output_filename": "pläne-treesta-import.csv",
            "field_values": {"atlas": "1"},
            "field_renames": {"date": "last_modified_date"},
        },
    )

    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.setupUi(self)

        self.plugin_dir = plugin_dir or os.path.dirname(__file__)

        # Auswahl des Datentyps ergänzen
        self._setup_data_type_selection()

        # UI-Verkabelung
        self.btnBrowse.clicked.connect(self.browse_input)
        self.btnConvert.clicked.connect(self.convert)
        self.btnOpenFolder.clicked.connect(self.open_output_folder)

        # Initialzustand
        self.labelStatus.setText("Bereit.")
        self.textEditUnmapped.clear()

    # --- Datentyp-Auswahl ----------------------------------------------------

    def _setup_data_type_selection(self):
        """
        Ergänzt die Auswahl des zu importierenden Datentyps.
        Permanente Bäume sind standardmäßig ausgewählt.
        """
        self.groupDataType = QGroupBox("Datentyp")
        data_type_layout = QHBoxLayout(self.groupDataType)

        data_type_layout.addWidget(QLabel("Importieren als:"))

        self.comboDataType = QComboBox()
        for data_type in self.DATA_TYPES:
            self.comboDataType.addItem(data_type["label"], data_type)

        self.comboDataType.setCurrentIndex(0)
        self.comboDataType.setToolTip(
            "Legt den Ziellayer, die Vorgabewerte und den Namen der "
            "erzeugten CSV-Datei fest."
        )

        data_type_layout.addWidget(self.comboDataType, 1)

        # Direkt unterhalb der Dateiauswahl einfügen
        self.verticalLayout.insertWidget(1, self.groupDataType)

    def _selected_data_type(self):
        """
        Liefert die Konfiguration des ausgewählten Datentyps.
        """
        data_type = self.comboDataType.currentData()
        if not data_type:
            return self.DATA_TYPES[0]
        return data_type

    def _apply_data_type_values(self, csv_path, data_type):
        """
        Ergänzt oder überschreibt nur die für den ausgewählten Datentyp
        vorgesehenen Felder. Alle anderen Felder bleiben unverändert.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Die erzeugte CSV-Datei wurde nicht gefunden: {csv_path}"
            )

        with open(
            csv_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as input_file:
            reader = csv.DictReader(
                input_file,
                delimiter=";",
                quotechar='"'
            )

            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        if not fieldnames:
            raise ValueError(
                "Die erzeugte CSV-Datei enthält keine Kopfzeile."
            )

        field_values = data_type.get("field_values", {})
        field_renames = data_type.get("field_renames", {})

        # Datentypabhängige Feldnamen anpassen. Das gemeinsame Feldmapping
        # erzeugt für "datum" zunächst "date". Flächen und Pläne erwarten
        # stattdessen "last_modified_date".
        for old_field, new_field in field_renames.items():
            if old_field not in fieldnames:
                continue

            if new_field in fieldnames:
                fieldnames.remove(old_field)
            else:
                field_index = fieldnames.index(old_field)
                fieldnames[field_index] = new_field

            for row in rows:
                old_value = row.pop(old_field, None)

                # Ein vorhandener Wert aus dem umzubenennenden Feld hat
                # Vorrang. Leere Werte überschreiben keinen bereits
                # vorhandenen Wert im Zielfeld.
                if old_value is not None and str(old_value).strip() != "":
                    row[new_field] = old_value

        for field_name in field_values:
            if field_name not in fieldnames:
                fieldnames.append(field_name)

        for row in rows:
            for field_name, field_value in field_values.items():
                row[field_name] = field_value

        with open(
            csv_path,
            "w",
            encoding="utf-8",
            newline=""
        ) as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=fieldnames,
                delimiter=";",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(rows)

    def _rename_output_csv(self, csv_path, output_filename):
        """
        Benennt die erzeugte Importdatei passend zum gewählten Ziellayer.
        Eine bereits vorhandene gleichnamige Datei wird ersetzt.
        """
        output_path = os.path.join(
            os.path.dirname(csv_path),
            output_filename
        )

        if os.path.abspath(csv_path) != os.path.abspath(output_path):
            os.replace(csv_path, output_path)

        return output_path

    # --- Helper ---------------------------------------------------------------

    def browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "CSV auswählen (BK3/BK4 Export)",
            "",
            "CSV (*.csv);;Alle Dateien (*.*)"
        )

        if path:
            self.lineEditInput.setText(path)
            self.labelStatus.setText(
                "Datei gewählt. Bereit zur Konvertierung."
            )

    def open_output_folder(self):
        input_path = self.lineEditInput.text().strip()
        output_directory = (
            os.path.dirname(input_path)
            if input_path
            else ""
        )

        if (
            not output_directory
            or not os.path.isdir(output_directory)
        ):
            QMessageBox.information(
                self,
                "Hinweis",
                "Kein gültiger Ausgabeordner gefunden."
            )
            return

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(output_directory)
        )

    def _set_busy(self, busy):
        enabled = not busy

        self.btnConvert.setEnabled(enabled)
        self.btnBrowse.setEnabled(enabled)
        self.btnOpenFolder.setEnabled(enabled)
        self.groupDataType.setEnabled(enabled)

    # --- Kernaktion -----------------------------------------------------------

    def convert(self):
        input_path = self.lineEditInput.text().strip()

        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(
                self,
                "Fehler",
                "Bitte zuerst eine gültige Eingabedatei wählen."
            )
            return

        data_type = self._selected_data_type()

        self._set_busy(True)
        self.labelStatus.setText(
            "⏳ Erkenne Profil und konvertiere …"
        )
        self.textEditUnmapped.clear()

        try:
            # Auto-Erkennung BK3/BK4 und Konvertierung
            out_csv, unmapped_txt, profile = smart_convert(
                input_path,
                self.plugin_dir
            )

            # Vorgabewerte des gewählten Datentyps schreiben
            self._apply_data_type_values(
                out_csv,
                data_type
            )

            # Ausgabedatei passend zum Ziellayer benennen
            out_csv = self._rename_output_csv(
                out_csv,
                data_type["output_filename"]
            )

            # Profil verständlich darstellen
            if profile == "baumkataster_3":
                profile_text = "Baumkataster 3"
            elif profile == "baumkataster_4":
                profile_text = "Baumkataster 4"
            else:
                profile_text = f"Unbekannt/extern ({profile})"

            self.labelStatus.setText(
                "✅ Umwandlung abgeschlossen – "
                f"erkanntes Profil: {profile_text}; "
                f"Datentyp: {data_type['label']}; "
                f"Datei: {data_type['output_filename']}"
            )

            # Nicht gemappte Werte anzeigen
            if os.path.exists(unmapped_txt):
                with open(
                    unmapped_txt,
                    "r",
                    encoding="utf-8"
                ) as unmapped_file:
                    self.textEditUnmapped.setPlainText(
                        unmapped_file.read()
                    )
            else:
                self.textEditUnmapped.clear()

            # Ausgabedatei prüfen
            if not os.path.exists(out_csv):
                QMessageBox.warning(
                    self,
                    "Warnung",
                    "Die Zieldatei wurde nicht gefunden."
                )

        except Exception as error:
            self.labelStatus.setText(
                "❌ Fehler bei der Konvertierung."
            )
            QMessageBox.critical(
                self,
                "Fehler",
                str(error)
            )

        finally:
            self._set_busy(False)
