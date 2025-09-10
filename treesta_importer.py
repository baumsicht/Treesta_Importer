from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os
from .treesta_importer_dialog import TreestaImporterDialog

class TreestaImporter:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.action = QAction(QIcon(icon_path), 'Treesta Importer', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu('Treesta Importer', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu('Treesta Importer', self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not self.dialog:
            self.dialog = TreestaImporterDialog(parent=self.iface.mainWindow(), plugin_dir=self.plugin_dir)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
