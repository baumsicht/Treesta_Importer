# -*- coding: utf-8 -*-
"""
converter_manager – steuert die Auswahl des passenden Converters (BK3/BK4)
und ist die einzige Schnittstelle für treesta_importer_dialog.py

- detect_profile() → "baumkataster_3" oder "baumkataster_4"
- smart_convert()  → ruft converter_bk3 / converter_bk4 mit den richtigen
                     mapping-Dateien auf und liefert:
                     (out_csv, unmapped_txt, profile)
"""

import csv
import os
import importlib


def detect_profile(input_csv_path: str) -> str:
    """
    Einfache Profil-Erkennung:

    - Wenn eine Kopfzeile mit 'Kontrollen_' beginnt → Baumkataster 3
    - sonst → Baumkataster 4
    """
    with open(input_csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        headers = next(reader, [])

    if any(h.startswith("Kontrollen_") for h in headers):
        return "baumkataster_3"
    return "baumkataster_4"


def _load_converter(profile: str):
    """
    Lädt das passende Converter-Modul.

    Erwartet:
    - profile == "baumkataster_3" → Modul .converter_bk3
    - profile == "baumkataster_4" → Modul .converter_bk4
    """
    if profile == "baumkataster_3":
        module_name = ".converter_bk3"
    elif profile == "baumkataster_4":
        module_name = ".converter_bk4"
    else:
        # Fallback: BK4 verwenden
        module_name = ".converter_bk4"

    try:
        return importlib.import_module(module_name, package=__package__)
    except Exception as e:
        raise RuntimeError(f"Converter-Modul '{module_name}' konnte nicht geladen werden: {e}")


def smart_convert(input_csv_path: str, plugin_dir: str):
    """
    Haupt-Einstiegspunkt für das Plugin.

    input_csv_path – ausgewählte BK3/BK4-CSV
    plugin_dir     – Plugin-Verzeichnis (für die Mapping-Dateien)

    Rückgabe:
        out_csv_path, unmapped_txt_path, profile ("baumkataster_3" / "baumkataster_4")
    """
    profile = detect_profile(input_csv_path)
    converter_module = _load_converter(profile)

    # Mapping-Dateien abhängig vom Profil
    if profile == "baumkataster_3":
        suffix = "bk3"
    else:
        suffix = "bk4"

    fields_mapping_path = os.path.join(plugin_dir, f"fields_mapping_baumkataster_{suffix}.csv")
    value_mapping_path = os.path.join(plugin_dir, f"value_mapping_baumkataster_{suffix}.csv")

    if not os.path.exists(fields_mapping_path):
        raise FileNotFoundError(f"Feldmapping nicht gefunden: {fields_mapping_path}")
    if not os.path.exists(value_mapping_path):
        raise FileNotFoundError(f"Wertmapping nicht gefunden: {value_mapping_path}")

    # Converter aufrufen (beide Versionen sollen dieselbe Signatur haben)
    out_csv, unmapped_txt = converter_module.convert_kataster(
        input_csv_path=input_csv_path,
        field_mapping_path=fields_mapping_path,
        value_mapping_path=value_mapping_path
    )

    return out_csv, unmapped_txt, profile
