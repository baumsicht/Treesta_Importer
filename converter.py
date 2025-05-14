import csv
import re
import os

def convert_kataster(input_data_path, output_path):
    plugin_dir = os.path.dirname(__file__)
    field_mapping_path = os.path.join(plugin_dir, "fields_mapping.csv")
    value_mapping_path = os.path.join(plugin_dir, "value_mapping.csv")
    unmapped_output_path = os.path.join(os.path.dirname(input_data_path), "unmapped_values.txt")

    prueffelder = [
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
        if not text or not text.startswith("{") or not text.endswith("}"):
            val_clean = text.replace(",", "").strip()
            if val_clean not in value_dict:
                unmapped_set.add(text)
            return value_dict.get(val_clean, text)
        inner = text.strip("{}").split(",")
        translated = []
        for item in inner:
            raw = item.strip()
            cleaned = raw.replace(",", "")
            mapped = value_dict.get(cleaned, raw)
            if cleaned not in value_dict:
                unmapped_set.add(raw)
            translated.append(mapped)
        return "{" + ", ".join(translated) + "}"

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

    with open(input_data_path, encoding="utf-8", newline='') as f:
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
            if new_key not in prueffelder:
                new_val = convert_booleans(val)
            else:
                new_val = map_compound_value_exact(val, value_dict, unmapped_values)
                new_val = convert_booleans(new_val)
            new_row[new_key] = new_val

        if "baumart" in row:
            new_row["species"] = clean_species(row["baumart"])

        output_rows.append(new_row)

    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f, f) for f in original_fields] + (["species"] if "species" in output_rows[0] else [])
    ))

    if unmapped_values:
        with open(unmapped_output_path, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (nach Entfernung von Kommas):\n\n")
            for val in sorted(unmapped_values):
                f.write(f"{val}\n")

    with open(output_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(output_rows)