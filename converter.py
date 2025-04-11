import csv
import re
import os

def clean_species(value):
    if value is None:
        return value
    # Entfernt führende Zahlen und Leerzeichen und alles in Klammern
    value = re.sub(r'^\d+\s*', '', value)
    value = re.sub(r'\s*\([^)]*\)', '', value)
    return value.strip()

def map_compound_value_exact(text, value_dict, unmapped_set):
    # Entferne die äußeren geschweiften Klammern und trimme den Inhalt
    key_whole = text.strip("{}").strip()
    # Prüfe, ob der gesamte Inhalt als Schlüssel existiert
    if key_whole in value_dict:
        return "{" + value_dict[key_whole] + "}"
    # Andernfalls: Splitte anhand des Kommas und mappe die einzelnen Bestandteile
    inner = key_whole.split(",")
    translated = []
    for item in inner:
        item_clean = item.strip()
        if item_clean not in value_dict:
            unmapped_set.add(item_clean)
        translated.append(value_dict.get(item_clean, item_clean))
    return "{" + ", ".join(translated) + "}"

def convert_booleans(val):
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower == "true":
            return "1"
        if lower == "false":
            return "0"
    return val

def convert_kataster(input_csv_path, field_mapping_path, value_mapping_path, output_dir):
    output_csv = os.path.join(output_dir, "treesta_import.csv")
    unmapped_txt = os.path.join(output_dir, "unmapped_values.txt")

    # Liste der Felder, bei denen das Werte-Mapping angewendet werden soll
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

    # Feld-Mapping laden
    field_dict = {}
    with open(field_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            field_dict[row["old_field"].strip()] = row["new_field"].strip()

    # Wert-Mapping laden
    value_dict = {}
    with open(value_mapping_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            value_dict[row["old_value"].strip()] = row["new_value"].strip()

    # Quelldaten laden
    with open(input_csv_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        input_rows = list(reader)
        original_fields = reader.fieldnames

    unmapped_values = set()
    output_rows = []

    for row in input_rows:
        new_row = {}
        for old_key, value in row.items():
            # Bestimme den neuen Feldnamen; falls nicht vorhanden, wird der alte Wert verwendet
            new_key = field_dict.get(old_key.strip(), old_key.strip())
            # Überprüfe, ob das Mapping für diesen Feldnamen angewendet werden soll
            if new_key not in prueffelder:
                new_val = convert_booleans(value)
            else:
                val = value.strip() if isinstance(value, str) else value
                if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                    new_val = map_compound_value_exact(val, value_dict, unmapped_values)
                else:
                    if val not in value_dict:
                        unmapped_values.add(val)
                    new_val = value_dict.get(val, val)
                new_val = convert_booleans(new_val)
            new_row[new_key] = new_val

        # Extrahiere "species" aus "baumart", falls vorhanden
        if "baumart" in row:
            new_row["species"] = clean_species(row["baumart"])

        output_rows.append(new_row)

    # Beibehaltung der ursprünglichen Spaltenreihenfolge, ggf. mit "species" als Anhang
    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f.strip(), f.strip()) for f in original_fields] +
        (["species"] if "species" in output_rows[0] else [])
    ))

    # Schreibe unmapped_values mit zusätzlicher Fehlermeldung in die Textdatei
    if unmapped_values:
        with open(unmapped_txt, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (value_mapping.csv ergänzen - möglicherweise inkonsistente Daten oder fehlerhafte Kommata):\n")
            for val in sorted(unmapped_values):
                f.write(f"{val}\n")

    # Exportiere die Daten als CSV mit Quotechar, um Fehler bei Kommata zu vermeiden
    with open(output_csv, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(output_rows)

    return output_csv, unmapped_txt if unmapped_values else None
