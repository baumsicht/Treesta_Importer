from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
import os
from .converter_manager import smart_convert

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'treesta_importer_dialog_base.ui'))

class TreestaImporterDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = plugin_dir or os.path.dirname(__file__)

        # UI Verkabelung
        self.btnBrowse.clicked.connect(self.browse_input)
        self.btnConvert.clicked.connect(self.convert)
        self.btnOpenFolder.clicked.connect(self.open_output_folder)

        # Initialzustand
        self.labelStatus.setText("Bereit.")
        self.textEditUnmapped.clear()

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
            self.labelStatus.setText("Datei gewählt. Bereit zur Konvertierung.")

    def open_output_folder(self):
        in_path = self.lineEditInput.text().strip()
        out_dir = os.path.dirname(in_path) if in_path else ""
        if not out_dir or not os.path.isdir(out_dir):
            QMessageBox.information(self, "Hinweis", "Kein gültiger Ausgabeordner gefunden.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(out_dir))

    def _set_busy(self, busy: bool):
        self.btnConvert.setEnabled(not busy)
        self.btnBrowse.setEnabled(not busy)
        self.btnOpenFolder.setEnabled(not busy)

    # --- Kernaktion -----------------------------------------------------------
    def convert(self):
        input_path = self.lineEditInput.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Fehler", "Bitte zuerst eine gültige Eingabedatei wählen.")
            return

        self._set_busy(True)
        self.labelStatus.setText("⏳ Erkenne Profil & konvertiere…")
        self.textEditUnmapped.clear()

        try:
            # Auto-Erkennung BK3/BK4 + Konvertierung
            out_csv, unmapped_txt, profile = smart_convert(input_path, self.plugin_dir)

            # Profil hübsch darstellen
            if profile == "baumkataster_3":
                profile_text = "Baumkataster 3"
            elif profile == "baumkataster_4":
                profile_text = "Baumkataster 4"
            else:
                profile_text = f"Unbekannt/extern ({profile})"

            self.labelStatus.setText(f"✅ Umwandlung abgeschlossen – erkanntes Profil: {profile_text}")

            # Unmapped anzeigen (falls vorhanden)
            if os.path.exists(unmapped_txt):
                with open(unmapped_txt, encoding="utf-8") as f:
                    self.textEditUnmapped.setPlainText(f.read())
            else:
                self.textEditUnmapped.clear()

            # Minimalprüfung: Ausgabedatei vorhanden?
            if not os.path.exists(out_csv):
                QMessageBox.warning(self, "Warnung", "Die Zieldatei wurde nicht gefunden.")

        except Exception as e:
            self.labelStatus.setText("❌ Fehler bei der Konvertierung.")
            QMessageBox.critical(self, "Fehler", str(e))
        finally:
            self._set_busy(False)
