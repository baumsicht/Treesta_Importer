import csv
import re
import os
from qgis.core import QgsProject

# === PROJEKT- UND PLUGINPFAD ERMITTELN ===
project_dir = os.path.dirname(QgsProject.instance().fileName())
plugin_dir = os.path.dirname(__file__)

# === DATEIPFADE DEFINIEREN ===
field_mapping_path = os.path.join(plugin_dir, "fields_mapping.csv")
value_mapping_path = os.path.join(plugin_dir, "value_mapping.csv")

# === ZU PRÜFENDE FELDER ===
prüffelder = [
    "condition", "vitality", "development", "safety_expectation", "tree_safety",
    "life_expectancy", "restriction", "features_crown", "features_trunk",
    "features_trunkbase_root_collar", "features_root_surroundings",
    "measures_1", "measures_1_urgency", "measures_1_access", "measures_1_approval",
    "measures_2", "measures_2_urgency", "measures_2_access", "measures_2_approval",
    "measures_3", "measures_3_urgency", "measures_3_access", "measures_3_approval",
    "measures_4", "measures_4_urgency", "measures_4_access", "measures_4_approval",
    "measures_5", "measures_5_urgency", "measures_5_access", "measures_5_approval",
    "habitat_structure_canopy", "habitat_species_canopy",
    "habitat_structure_trunk", "habitat_species_trunk",
    "habitat_affected", "habitat_avoidance", "habitat_mitigation", "habitat_replacement"
]

# === HILFSFUNKTIONEN ===
def clean_species(value):
    if value is None:
        return value
    value = re.sub(r'^\d+\s*', '', value)
    value = re.sub(r'\s*\([^)]*\)', '', value)
    return value.strip()

def map_compound_value_exact(text, value_dict, unmapped_set):
    if not text:
        return text

    full_clean = text.strip()
    if full_clean.startswith("{") and full_clean.endswith("}"):
        inner = full_clean.strip("{}").strip()

        # Fall 1: kompletter Eintrag in value_dict vorhanden (z. B. mit Komma)
        if inner in value_dict:
            return "{" + value_dict[inner] + "}"

        # Fall 2: Einzelwert mit Komma, aber nicht direkt im Mapping → Kommas entfernen und erneut prüfen
        inner_clean = inner.replace(",", "")
        if inner_clean in value_dict:
            return "{" + value_dict[inner_clean] + "}"

        # Fall 3: mehrere Werte – aufteilen
        parts = [p.strip() for p in inner.split(",")]
        translated = []
        for item in parts:
            if item not in value_dict:
                unmapped_set.add(item)
            translated.append(value_dict.get(item, item))
        return "{" + ", ".join(translated) + "}"

    # Kein {...}, normaler Einzelwert
    val = text.strip()
    val_clean = val.replace(",", "")
    if val_clean not in value_dict:
        unmapped_set.add(val_clean)
    return value_dict.get(val_clean, val_clean)

def convert_booleans(val):
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower == "true":
            return "1"
        if lower == "false":
            return "0"
    return val

# === HAUPTFUNKTION ===
def convert_kataster(input_csv_path, output_csv_path):
    unmapped_output_path = os.path.join(os.path.dirname(output_csv_path), "unmapped_values.txt")

    # Mapping-Tabellen laden
    field_dict = {}
    with open(field_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            field_dict[row["old_field"]] = row["new_field"]

    value_dict = {}
    with open(value_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            key = row["old_value"].strip().replace(",", "")
            value_dict[key] = row["new_value"].strip()

    # Quelldaten einlesen
    with open(input_csv_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        input_rows = list(reader)
        original_fields = reader.fieldnames

    unmapped_values = set()
    output_rows = []

    for row in input_rows:
        new_row = {}
        for old_key, value in row.items():
            new_key = field_dict.get(old_key, old_key)
            val = value.strip() if isinstance(value, str) else value

            if new_key not in prüffelder:
                new_val = convert_booleans(val)
            else:
                new_val = map_compound_value_exact(val, value_dict, unmapped_values)
                new_val = convert_booleans(new_val)

            new_row[new_key] = new_val

        if "baumart" in row:
            new_row["species"] = clean_species(row["baumart"])

        output_rows.append(new_row)

    # Feldreihenfolge beibehalten + species anhängen
    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f, f) for f in original_fields] + (["species"] if "species" in output_rows[0] else [])
    ))

    # Nicht gemappte Werte speichern
    if unmapped_values:
        with open(unmapped_output_path, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (value_mapping.csv ergänzen):\n")
            for val in sorted(unmapped_values):
                f.write(f"{val}\n")

    # CSV exportieren
    with open(output_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(output_rows)

    return output_csv_path, unmapped_output_path
