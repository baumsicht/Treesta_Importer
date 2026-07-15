# -*- coding: utf-8 -*-

import csv
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
)

from .converter_manager import smart_convert


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(
        os.path.dirname(__file__),
        "treesta_importer_dialog_base.ui"
    )
)


class TreestaImporterDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.setupUi(self)

        self.plugin_dir = plugin_dir or os.path.dirname(__file__)

        # Auswahl des Baumtyps ergänzen
        self._setup_tree_type_selection()

        # UI-Verkabelung
        self.btnBrowse.clicked.connect(self.browse_input)
        self.btnConvert.clicked.connect(self.convert)
        self.btnOpenFolder.clicked.connect(self.open_output_folder)

        # Initialzustand
        self.labelStatus.setText("Bereit.")
        self.textEditUnmapped.clear()

    # --- Baumtyp-Auswahl ------------------------------------------------------

    def _setup_tree_type_selection(self):
        """
        Ergänzt die Auswahl zwischen permanenten und temporären Bäumen.

        Permanente Bäume: temp = 0
        Temporäre Bäume:  temp = 1
        """
        self.groupTreeType = QGroupBox("Baumtyp")

        tree_type_layout = QHBoxLayout(self.groupTreeType)

        self.radioPermanent = QRadioButton("Permanente Bäume")
        self.radioTemporary = QRadioButton("Temporäre Bäume")

        # Standardauswahl
        self.radioPermanent.setChecked(True)

        self.radioPermanent.setToolTip(
            "Alle Bäume dieser CSV werden mit temp = 0 importiert."
        )
        self.radioTemporary.setToolTip(
            "Alle Bäume dieser CSV werden mit temp = 1 importiert."
        )

        tree_type_layout.addWidget(self.radioPermanent)
        tree_type_layout.addWidget(self.radioTemporary)
        tree_type_layout.addStretch()

        # Direkt unterhalb der Dateiauswahl einfügen
        self.verticalLayout.insertWidget(1, self.groupTreeType)

    def _selected_temp_value(self):
        """
        Liefert den für die gesamte CSV gewählten temp-Wert.
        """
        if self.radioTemporary.isChecked():
            return "1"

        return "0"

    def _apply_temp_value(self, csv_path, temp_value):
        """
        Ergänzt oder überschreibt die Spalte 'temp' in der erzeugten CSV.

        Dadurch müssen die einzelnen BK3-/BK4-Converter nicht angepasst
        werden.
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

        # Spalte ergänzen, wenn sie noch nicht vorhanden ist
        if "temp" not in fieldnames:
            fieldnames.append("temp")

        # Gewählten Wert für alle Datensätze setzen
        for row in rows:
            row["temp"] = temp_value

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
        self.groupTreeType.setEnabled(enabled)

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

        temp_value = self._selected_temp_value()

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

            # Gewählten Baumtyp in die Ausgabedatei schreiben
            self._apply_temp_value(
                out_csv,
                temp_value
            )

            # Profil verständlich darstellen
            if profile == "baumkataster_3":
                profile_text = "Baumkataster 3"
            elif profile == "baumkataster_4":
                profile_text = "Baumkataster 4"
            else:
                profile_text = f"Unbekannt/extern ({profile})"

            if temp_value == "1":
                tree_type_text = "temporäre Bäume"
            else:
                tree_type_text = "permanente Bäume"

            self.labelStatus.setText(
                "✅ Umwandlung abgeschlossen – "
                f"erkanntes Profil: {profile_text}; "
                f"Baumtyp: {tree_type_text}"
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