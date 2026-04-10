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

# Feste BK-Maßnahmenlogik:
# Quellfeld -> (Treesta measures-Feld, Treesta urgency-Feld, urgency-Wert)
MEASURE_URGENCY_FIELDS = {
    "massnahme_hoch": ("measures_1", "measures_1_urgency", "urgent"),
    "massnahme_normal": ("measures_2", "measures_2_urgency", "normal"),
    "massnahme_niedrig": ("measures_3", "measures_3_urgency", "low"),
    "massnahme_sofort": ("measures_4", "measures_4_urgency", "immediately"),
    "massnahme_optional": ("measures_5", "measures_5_urgency", "optional"),
}


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


def normalize_text(val):
    """
    Allgemeine Text-Normalisierung:
    - trim
    - äußere einfache/doppelte Anführungszeichen entfernen
    - Mehrfach-Leerzeichen reduzieren
    """
    if not isinstance(val, str):
        return val
    val = val.strip()
    val = val.strip('"').strip("'").strip()
    val = re.sub(r"\s+", " ", val)
    return val.strip()


def strip_leading_code(val):
    """
    Führende numerische Codes entfernen:
    - 01 Totholzentfernung -> Totholzentfernung
    - 011 Maßnahme -> Maßnahme
    """
    if not isinstance(val, str):
        return val
    val = normalize_text(val)
    val = re.sub(r"^\d+\s*", "", val)
    return val.strip()


def normalize_mapping_key(val):
    """
    Schlüssel für das Value-Mapping normalisieren.
    Wichtig: führende Zahlen werden ignoriert.
    """
    if not isinstance(val, str):
        return val
    val = normalize_text(val)
    val = strip_leading_code(val)
    return val


def should_track_unmapped(target_key: str, raw_value: str) -> bool:
    """
    Nur sinnvolle unmapped-Werte sammeln.
    """
    if not raw_value or not isinstance(raw_value, str):
        return False

    v = normalize_text(raw_value)
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


def load_csv_mapping(path, key_col, value_col, label):
    """
    CSV-Mapping robust laden.
    Erwartet z. B.:
      old_value;new_value
      old_field;new_field
    """
    mapping = {}

    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ";"

        reader = csv.DictReader(f, delimiter=delimiter)

        if not reader.fieldnames:
            raise ValueError(f"{label}: keine Header gefunden in {path}")

        header_map = {}
        for fn in reader.fieldnames:
            if fn is not None:
                cleaned = fn.strip().lstrip("\ufeff")
                header_map[cleaned] = fn

        if key_col not in header_map or value_col not in header_map:
            found = [fn.strip() if fn else fn for fn in reader.fieldnames]
            raise ValueError(
                f"{label}: erwartete Spalten '{key_col}' und '{value_col}' nicht gefunden in {path}. "
                f"Gefundene Header: {found}"
            )

        real_key_col = header_map[key_col]
        real_value_col = header_map[value_col]

        for row in reader:
            raw_key = row.get(real_key_col)
            raw_value = row.get(real_value_col)

            if raw_key is None:
                continue

            k = normalize_text(raw_key)
            v = normalize_text(raw_value or "")

            if not k:
                continue

            if key_col == "old_value":
                nk = normalize_mapping_key(k)
                if nk:
                    mapping[nk] = v
            else:
                mapping[k] = v

    if not mapping:
        raise ValueError(f"{label}: keine Mapping-Einträge geladen aus {path}")

    return mapping


def map_single_value(val, value_dict, unmapped_set, target_key=""):
    """
    Einzelwert mappen.
    Führende Zahlen im Quellwert werden ignoriert.
    """
    original_val = normalize_text(val)
    if not original_val:
        return original_val

    normalized_val = normalize_mapping_key(original_val)

    if normalized_val in value_dict:
        return value_dict[normalized_val]

    if should_track_unmapped(target_key, original_val):
        unmapped_set.add(original_val)

    return original_val


def parse_braced_values(inner_text):
    """
    Parst Inhalte wie:
      "A","B","C, mit Komma"
    korrekt unter Beachtung von Anführungszeichen.
    """
    if not isinstance(inner_text, str):
        return []

    inner_text = inner_text.strip()
    if not inner_text:
        return []

    try:
        reader = csv.reader(
            [inner_text],
            delimiter=",",
            quotechar='"',
            skipinitialspace=True
        )
        parts = next(reader, [])
        parts = [normalize_text(p) for p in parts if normalize_text(p)]
        if parts:
            return parts
    except Exception:
        pass

    return []


def split_compound_parts(text, has_braces=False):
    """
    Zerlegt Mehrfachwerte robust.

    Fälle:
    1. In {...} mit Quotes:
       "A","B","C, mit Komma"
    2. BK-Typ mit Codes:
       01 Totholzentfernung, 25 Kronenpflege
    3. Normale Liste:
       A,B,C
    """
    text = text.strip() if isinstance(text, str) else text
    if not text:
        return []

    # Fall 1: Inhalte aus {...} mit Quotes korrekt parsen
    if has_braces and '"' in text:
        parsed = parse_braced_values(text)
        if parsed:
            return parsed

    normalized = normalize_text(text)
    if not normalized:
        return []

    # Fall 2: BK-Typ mit Codes
    parts = re.split(r',\s*(?=\d+\s*)', normalized)
    if len(parts) > 1:
        return [normalize_text(p) for p in parts if normalize_text(p)]

    # Fall 3: normale kommagetrennte Liste
    if "," in normalized:
        parts = [normalize_text(p) for p in normalized.split(",")]
        return [p for p in parts if p]

    return [normalized]


def map_compound_value_exact(text, value_dict, unmapped_set, target_key=""):
    if not text or not isinstance(text, str):
        return text

    raw_text = text.strip()
    if not raw_text:
        return text

    has_braces = raw_text.startswith("{") and raw_text.endswith("}")
    inner = raw_text[1:-1].strip() if has_braces else raw_text

    if not inner:
        return "{}" if has_braces else ""

    # 1. Ganzen Ausdruck direkt prüfen
    normalized_inner = normalize_mapping_key(inner)
    if normalized_inner in value_dict:
        mapped = value_dict[normalized_inner]
        if has_braces:
            return '{"' + mapped + '"}'
        return mapped

    # 2. Problematische Einzelwerte mit Komma prüfen
    inner_no_commas = normalize_text(inner.replace(",", ""))
    normalized_inner_no_commas = normalize_mapping_key(inner_no_commas)
    if normalized_inner_no_commas in value_dict:
        mapped = value_dict[normalized_inner_no_commas]
        if has_braces:
            return '{"' + mapped + '"}'
        return mapped

    # 3. Als Mehrfachwert behandeln
    parts = split_compound_parts(inner, has_braces=has_braces)

    if len(parts) == 1:
        mapped = map_single_value(parts[0], value_dict, unmapped_set, target_key=target_key)
        if has_braces:
            return '{"' + mapped + '"}'
        return mapped

    translated = []
    for part in parts:
        mapped = map_single_value(part, value_dict, unmapped_set, target_key=target_key)
        translated.append(mapped)

    if has_braces:
        return "{" + ",".join(f'"{v}"' for v in translated) + "}"

    return ", ".join(translated)


def is_effectively_empty_measure_value(value):
    """
    Prüft, ob ein Maßnahmenwert als leer gelten soll.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False

    v = value.strip()
    return v in {"", "{}", '{""}'}


def convert_kataster(input_csv_path, field_mapping_path=None, value_mapping_path=None):
    """
    Plugin-kompatible Signatur:
      convert_kataster(input_csv_path, field_mapping_path=None, value_mapping_path=None)

    Output im selben Ordner:
      treesta_import.csv + unmapped_values.txt
    """
    plugin_dir = os.path.dirname(__file__)
    project_dir = os.path.dirname(input_csv_path)

    output_csv_path = os.path.join(project_dir, "treesta_import.csv")
    unmapped_output_path = os.path.join(project_dir, "unmapped_values.txt")

    # Fallback: falls manager keine Pfade übergibt
    if not field_mapping_path:
        for fn in (
            "fields_mapping_baumkataster_bk4.csv",
            "fields_mapping_baumkataster_4.csv",
            "fields_mapping.csv"
        ):
            p = os.path.join(plugin_dir, fn)
            if os.path.exists(p):
                field_mapping_path = p
                break

    if not value_mapping_path:
        for fn in (
            "value_mapping_baumkataster_bk4.csv",
            "value_mapping_baumkataster_4.csv",
            "value_mapping.csv"
        ):
            p = os.path.join(plugin_dir, fn)
            if os.path.exists(p):
                value_mapping_path = p
                break

    if not field_mapping_path or not os.path.exists(field_mapping_path):
        raise FileNotFoundError(f"fields_mapping nicht gefunden: {field_mapping_path}")

    if not value_mapping_path or not os.path.exists(value_mapping_path):
        raise FileNotFoundError(f"value_mapping nicht gefunden: {value_mapping_path}")

    # Mapping laden
    field_dict = load_csv_mapping(field_mapping_path, "old_field", "new_field", "fields_mapping")
    value_dict = load_csv_mapping(value_mapping_path, "old_value", "new_value", "value_mapping")

    print(f"field_mapping_path: {field_mapping_path}")
    print(f"value_mapping_path: {value_mapping_path}")
    print(f"Anzahl field mappings: {len(field_dict)}")
    print(f"Anzahl value mappings: {len(value_dict)}")

    # Input lesen
    with open(input_csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        input_rows = list(reader)
        original_fields = reader.fieldnames or []

    # Verarbeitung
    unmapped_values = set()
    output_rows = []

    for row in input_rows:
        new_row = {}

        for old_key, value in row.items():
            val = value.strip() if isinstance(value, str) else value

            # Sonderlogik für Maßnahmen + Dringlichkeit
            if old_key in MEASURE_URGENCY_FIELDS:
                target_measure, target_urgency, urgency_value = MEASURE_URGENCY_FIELDS[old_key]

                mapped_val = map_compound_value_exact(
                    val,
                    value_dict,
                    unmapped_values,
                    target_key=target_measure
                )
                mapped_val = convert_booleans(mapped_val)

                new_row[target_measure] = mapped_val

                if not is_effectively_empty_measure_value(mapped_val):
                    new_row[target_urgency] = urgency_value

                continue

            # Normale Feldverarbeitung
            new_key = field_dict.get(old_key, old_key)

            if new_key not in PRUEFFELDER:
                new_val = convert_booleans(val)
            else:
                new_val = map_compound_value_exact(
                    val,
                    value_dict,
                    unmapped_values,
                    target_key=new_key
                )
                new_val = convert_booleans(new_val)

            new_row[new_key] = new_val

        if "baumart" in row:
            new_row["species"] = clean_species(row["baumart"])

        output_rows.append(new_row)

    # Spaltenreihenfolge
    output_fieldnames = list(dict.fromkeys(
        [field_dict.get(f, f) for f in original_fields] +
        (["species"] if output_rows and "species" in output_rows[0] else [])
    ))

    # Sicherstellen, dass measures_*_urgency auch in den Output-Spalten stehen,
    # selbst wenn sie nicht in original_fields/feldmapping auftauchen
    for _, (measure_field, urgency_field, _) in MEASURE_URGENCY_FIELDS.items():
        if measure_field in output_fieldnames and urgency_field not in output_fieldnames:
            output_fieldnames.append(urgency_field)

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
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
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