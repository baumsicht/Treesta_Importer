
def classFactory(iface):
    from .treesta_importer import TreestaImporter
    return TreestaImporter(iface)
