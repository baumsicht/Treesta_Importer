# -*- coding: utf-8 -*-
import csv
import re
import os

# === ZU PRÜFENDE FELDER ===
PRUEFFELDER = [
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

# unmapped_values: diese Feldnamen/Teile ignorieren
IGNORE_UNMAPPED_SUBSTRINGS = (
    "foto", "photo", "image", "bild", "anhang", "attachment",
    "bemerk", "kommentar", "comment", "note", "notiz",
    "name",
    "datum", "date", "time", "timestamp",
    "wkt", "geom", "geometry",
    "straße", "strasse", "street", "ort", "city", "zip", "plz",
)

INT_RE = re.compile(r"^\d+$")


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


def should_track_unmapped(target_key: str, raw_value: str) -> bool:
    """
    Nur sinnvolle unmapped-Werte sammeln.
    """
    if not raw_value or not isinstance(raw_value, str):
        return False
    v = raw_value.strip()
    if not v:
        return False
    lv = v.lower()
    if lv in {"true", "false", "0", "1", "ja", "nein"}:
        return False
    if INT_RE.match(v):
        return False

    tk = (target_key or "").strip().lower()
    for sub in IGNORE_UNMAPPED_SUBSTRINGS:
        if sub in tk:
            return False
    return True


def map_compound_value_exact(text, value_dict, unmapped_set, target_key=""):
    if not text or not isinstance(text, str):
        return text

    if not (text.startswith("{") and text.endswith("}")):
        val = text.strip()
        if val and val not in value_dict and should_track_unmapped(target_key, val):
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
        part = parts[0].strip()
        if part and part not in value_dict and should_track_unmapped(target_key, part):
            unmapped_set.add(part)
        return "{" + value_dict.get(part, part) + "}"

    # 4. Mehrere Werte mappen
    translated = []
    for part in parts:
        part = part.strip()
        if part and part not in value_dict and should_track_unmapped(target_key, part):
            unmapped_set.add(part)
        translated.append(value_dict.get(part, part))
    return "{" + ", ".join(translated) + "}"


def convert_kataster(input_csv_path, field_mapping_path=None, value_mapping_path=None):
    """
    Neue Plugin-kompatible Signatur:
      convert_kataster(input_csv_path, field_mapping_path=None, value_mapping_path=None)

    Output wird wie erwartet im selben Ordner erzeugt:
      treesta_import.csv + unmapped_values.txt
    """
    plugin_dir = os.path.dirname(__file__)
    project_dir = os.path.dirname(input_csv_path)

    output_csv_path = os.path.join(project_dir, "treesta_import.csv")
    unmapped_output_path = os.path.join(project_dir, "unmapped_values.txt")

    # Fallback: falls manager keine Pfade übergibt
    if not field_mapping_path:
        # alte Namen (Mai-Version) UND neue Namen (Plugin) versuchen
        for fn in ("fields_mapping_baumkataster_bk4.csv", "fields_mapping_baumkataster_4.csv", "fields_mapping.csv"):
            p = os.path.join(plugin_dir, fn)
            if os.path.exists(p):
                field_mapping_path = p
                break

    if not value_mapping_path:
        for fn in ("value_mapping_baumkataster_bk4.csv", "value_mapping_baumkataster_4.csv", "value_mapping.csv"):
            p = os.path.join(plugin_dir, fn)
            if os.path.exists(p):
                value_mapping_path = p
                break

    if not field_mapping_path or not os.path.exists(field_mapping_path):
        raise FileNotFoundError(f"fields_mapping nicht gefunden: {field_mapping_path}")
    if not value_mapping_path or not os.path.exists(value_mapping_path):
        raise FileNotFoundError(f"value_mapping nicht gefunden: {value_mapping_path}")

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
        original_fields = reader.fieldnames or []

    # Verarbeitung
    unmapped_values = set()
    output_rows = []

    for row in input_rows:
        new_row = {}
        for old_key, value in row.items():
            new_key = field_dict.get(old_key, old_key)
            val = value.strip() if isinstance(value, str) else value

            if new_key not in PRUEFFELDER:
                new_val = convert_booleans(val)
            else:
                new_val = map_compound_value_exact(val, value_dict, unmapped_values, target_key=new_key)
                new_val = convert_booleans(new_val)

            new_row[new_key] = new_val

        if "baumart" in row:
            new_row["species"] = clean_species(row["baumart"])

        output_rows.append(new_row)

    # Spaltenreihenfolge
    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f, f) for f in original_fields] + (["species"] if output_rows and "species" in output_rows[0] else [])
    ))

    # Ungemappte Werte speichern
    if unmapped_values:
        with open(unmapped_output_path, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (value_mapping ergänzen):\n")
            for val in sorted(unmapped_values):
                f.write(f"{val}\n")
    else:
        if os.path.exists(unmapped_output_path):
            os.remove(unmapped_output_path)

    # Output schreiben
    with open(output_csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_fieldnames,
            delimiter=";",
            quotechar='"',
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return output_csv_path, unmapped_output_path
