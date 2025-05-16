from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QUrl
from qgis.utils import iface
import os
import webbrowser
from .converter import convert_kataster

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'treesta_importer_dialog_base.ui'))

class TreestaImporterDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.btnBrowse.clicked.connect(self.browse_input)
        self.btnConvert.clicked.connect(self.convert)
        self.btnOpenFolder.clicked.connect(self.open_output_folder)
        self.output_folder = None  # Wird später gesetzt

    def browse_input(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Altes Kataster wählen", "", "CSV-Dateien (*.csv)")
        if file_path:
            self.lineEditInput.setText(file_path)

    def convert(self):
        input_path = self.lineEditInput.text().strip()
        if not input_path or not os.path.exists(input_path):
            self.labelStatus.setText("⚠ Bitte eine gültige CSV-Datei auswählen!")
            return

        base_dir = os.path.dirname(input_path)
        output_csv = os.path.join(base_dir, "treesta_import.csv")

        try:
            output_csv, unmapped_path = convert_kataster(input_path, output_csv)
            self.labelStatus.setText("✅ Umwandlung abgeschlossen!")
            self.output_folder = base_dir

            # Nicht gemappte Werte anzeigen
            if os.path.exists(unmapped_path):
                with open(unmapped_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.textEditUnmapped.setPlainText(content)
            else:
                self.textEditUnmapped.setPlainText("Alle Werte konnten erfolgreich übersetzt werden.")

        except Exception as e:
            self.labelStatus.setText(f"❌ Fehler: {str(e)}")

    def open_output_folder(self):
        if self.output_folder and os.path.exists(self.output_folder):
            webbrowser.open(f'file:///{self.output_folder}')
        else:
            QMessageBox.warning(self, "Fehler", "Kein Ausgabeordner verfügbar.")
