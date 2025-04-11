from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog
import os
from .converter import convert_kataster

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'treesta_importer_dialog_base.ui'))

class TreestaImporterDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.btnBrowse.clicked.connect(self.browse_input)
        self.btnConvert.clicked.connect(self.convert)

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
        field_mapping_path = os.path.join(os.path.dirname(__file__), "fields_mapping.csv")
        value_mapping_path = os.path.join(os.path.dirname(__file__), "value_mapping.csv")
        try:
            output_csv, unmapped_txt = convert_kataster(input_path, field_mapping_path, value_mapping_path, base_dir)
            self.labelStatus.setText("✅ Umwandlung abgeschlossen!")
        except Exception as e:
            self.labelStatus.setText(f"❌ Fehler: {str(e)}")
