import csv
import re
import os

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

def clean_species(value):
    if value is None:
        return value
    value = re.sub(r'^\d+\s*', '', value)
    value = re.sub(r'\s*\([^)]*\)', '', value)
    return value.strip()

def convert_booleans(val):
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower == "true":
            return "1"
        if lower == "false":
            return "0"
    return val

def map_compound_value_exact(text, value_dict, unmapped_set):
    if not text or not isinstance(text, str):
        return text

    if not (text.startswith("{") and text.endswith("}")):
        val = text.strip()
        if val not in value_dict:
            unmapped_set.add(val)
        return value_dict.get(val, val)

    inner = text.strip("{}").strip()

    # 1. Kompletter Ausdruck exakt im Mapping?
    if inner in value_dict:
        return "{" + value_dict[inner] + "}"

    # 2. Kommas entfernt → prüfen
    inner_clean = inner.replace(",", "")
    if inner_clean in value_dict:
        return "{" + value_dict[inner_clean] + "}"

    # 3. Split mit RegEx an ", <Zahl>"
    parts = re.split(r', (?=\d{2,})', inner)
    if len(parts) == 1:
        part = parts[0]
        if part not in value_dict:
            unmapped_set.add(part)
        return "{" + value_dict.get(part, part) + "}"

    # 4. Mehrere Werte mappen
    translated = []
    for part in parts:
        part = part.strip()
        if part not in value_dict:
            unmapped_set.add(part)
        translated.append(value_dict.get(part, part))
    return "{" + ", ".join(translated) + "}"

def convert_kataster(input_csv_path, output_csv_path):
    plugin_dir = os.path.dirname(__file__)
    project_dir = os.path.dirname(input_csv_path)

    field_mapping_path = os.path.join(plugin_dir, "fields_mapping.csv")
    value_mapping_path = os.path.join(plugin_dir, "value_mapping.csv")
    unmapped_output_path = os.path.join(project_dir, "unmapped_values.txt")

    # Mapping laden
    field_dict = {}
    with open(field_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            field_dict[row["old_field"]] = row["new_field"]

    value_dict = {}
    with open(value_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            value_dict[row["old_value"].strip()] = row["new_value"].strip()

    # Input lesen
    with open(input_csv_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        input_rows = list(reader)
        original_fields = reader.fieldnames

    # Verarbeitung
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

    # Spaltenreihenfolge
    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f, f) for f in original_fields] + (["species"] if "species" in output_rows[0] else [])
    ))

    # Ungemappte Werte speichern
    if unmapped_values:
        with open(unmapped_output_path, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (value_mapping.csv ergänzen – ggf. inkonsistente Daten oder Probleme mit Trennung):\n")
            for val in sorted(unmapped_values):
                f.write(f"{val}\n")

    # Output schreiben
    with open(output_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(output_rows)

    return output_csv_path, unmapped_output_path
