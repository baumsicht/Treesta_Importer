# -*- coding: utf-8 -*-
"""
Treesta Importer – Konverter für Baumkataster 3/4 → Treesta-CSV

- Auto-Erkennung BK3/BK4 anhand Kopfzeilen (Kontrollen_* => BK3, sonst BK4).
- Maßnahmen:
  * BK3: measures_N + measures_N_urgency werden eingelesen und ab measures_1 verdichtet.
  * BK4: massnahme_hoch/normal/niedrig/sofort/optional werden erkannt und mit passender urgency gebündelt.
- Sortierung der Maßnahmen (höchste Priorität zuerst): high → normal → low → optional → leer.
- Aggregatfelder (Features/Habitat/Restriction) werden gesammelt und als {…} ausgegeben.
- condition/vitality: Kontrollen_* bevorzugt, zustand/vitalitaet als Fallback; "1 gut" -> "gut".
- Koordinaten (inkl. WKT): 1:1-Passthrough – auch ohne Mapping.
- unmapped_values.txt: IDs/Nummern, Adressen, Namen, Datum/Zeit, einfache Zahlen, true/false,
  Kommentar-/Bemerkungs-/Foto-/Anhang-/Bild-Felder sowie Koordinaten werden ignoriert.
"""

import csv
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Iterable

# === Aggregierbare Ziel-Felder ===
AGGREGATE_TARGETS = {
    "restriction",
    "features_crown",
    "features_trunk",
    "features_trunkbase_root_collar",
    "features_root_surroundings",
    "habitat_structure_canopy",
    "habitat_species_canopy",
    "habitat_structure_trunk",
    "habitat_species_trunk",
}

# === Alias & Priorität für Zustand/Vitalität ===
ALIAS_TARGETS = {
    "Kontrollen_zustand": "condition",
    "zustand": "condition",
    "Kontrollen_vitalitaet": "vitality",
    "vitalitaet": "vitality",
}
TARGET_PRIORITY = {
    "condition": {"Kontrollen_zustand": 0, "zustand": 1},
    "vitality": {"Kontrollen_vitalitaet": 0, "vitalitaet": 1},
}

# === BK4: Maßnahmen-Feld → Urgency ===========================================
BK4_MASSNAHME_URGENCY = {
    "massnahme_hoch": "high",
    "massnahme_normal": "normal",
    "massnahme_niedrig": "low",
    "massnahme_sofort": "high",
    "massnahme_optional": "low",  # ggf. auf "optional" ändern
}
BK4_MASSNAHME_PREFIX = "massnahme_"

# === Koordinaten-Passthrough (inkl. WKT) =====================================
COORD_TARGETS = {
    "x", "y", "lat", "lon", "lng", "latitude", "longitude",
    "easting", "northing",
    "coordinate_x", "coordinate_y", "koord_x", "koord_y",
    "wkt",
}
COORD_SYNONYMS = {"geom", "geometry", "the_geom"}  # optionale Synonyme

def is_coord_name(name: str) -> bool:
    if not name:
        return False
    ln = name.strip().lower()
    return ln in COORD_TARGETS or ln in COORD_SYNONYMS

# === Unmapped-Filter ==========================================================
IGNORE_UNMAPPED_TARGETS = {
    "id", "treenumber", "treenumber2", "sequencenumber", "number",
    "street", "location", "green_space", "land_use", "access", "city", "zip",
    "customer", "client", "owner", "contact", "inspector", "controller", "name",
    "date", "created_at", "updated_at", "timestamp", "inspection_date",
    "control_date", "measured_at", "survey_date", "last_control_date",
    *COORD_TARGETS, *COORD_SYNONYMS,
}

IGNORE_UNMAPPED_SUBSTRINGS = (
    # Adressen, Zeitliches etc.
    "name", "nummer", "number", "street", "straße", "strasse", "ort",
    "green_space", "location", "date", "time",
    # Kommentare / Bemerkungen
    "bemerkung", "bemerk", "kommentar",
    "comment", "comments", "remark",
    "note", "notes", "notiz", "notizen",
    # Medien/Anhänge
    "foto", "anhang", "attachment", "image", "bild",
    # Koordinaten
    "koordinat", "coord",
)

ISO_TS_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}')
SLASH_TS_RE = re.compile(r'^\d{4}/\d{2}/\d{2}[ T]\d{2}:\d2:\d2'.replace(':d2', r'\d{2}'))  # kleiner Trick wegen Rawstring
DATE_RE = re.compile(r'^\d{4}[-/]\d{2}[-/]\d{2}$')
INT_RE = re.compile(r'^\d+$')

def should_track_unmapped(target_key: str, raw_value: str) -> bool:
    if not raw_value:
        return False
    v = raw_value.strip()
    if not v:
        return False
    lv = v.lower()
    if lv in {"true", "false", "0", "1", "ja", "nein"}:
        return False
    if INT_RE.match(v):
        return False
    if ISO_TS_RE.match(v) or SLASH_TS_RE.match(v) or DATE_RE.match(v):
        return False
    tk = (target_key or "").strip().lower()
    if tk in (x.lower() for x in IGNORE_UNMAPPED_TARGETS):
        return False
    for sub in IGNORE_UNMAPPED_SUBSTRINGS:
        if sub in tk:
            return False
    return True

# === Helfer ===================================================================
def clean_species(value: str) -> str:
    if value is None:
        return ""
    v = re.sub(r'^\s*\d+\s*', '', value)
    v = re.sub(r'\s*\([^)]*\)', '', v)
    return v.strip()

def convert_booleans(val):
    if isinstance(val, str):
        s = val.strip().lower()
        if s == "true":
            return "1"
        if s == "false":
            return "0"
    return val

def to_braced(values: Iterable[str]) -> str:
    seen = set()
    out = []
    for v in values:
        if not v:
            continue
        sv = str(v).strip()
        if not sv:
            continue
        if sv.startswith("{") and sv.endswith("}"):
            sv = sv[1:-1].strip()
        if sv and sv not in seen:
            seen.add(sv)
            out.append(sv)
    if not out:
        return ""
    if len(out) == 1:
        return "{" + out[0] + "}"
    return "{" + ", ".join(out) + "}"

# === Mapping-CSV-Loader =======================================================
def load_field_mapping(path: str) -> Tuple[Dict[str, str], List[str], Dict[str, str]]:
    field_map: Dict[str, str] = {}
    target_order: List[str] = []
    with open(path, encoding="utf-8", newline='') as f:
        r = csv.DictReader(f, delimiter=";")
        cols = [c.strip().lower() for c in (r.fieldnames or [])]
        if {"old_field", "new_field"}.issubset(cols):
            key_old, key_new = "old_field", "new_field"
        elif {"source_field", "target_field"}.issubset(cols):
            key_old, key_new = "source_field", "target_field"
        else:
            raise ValueError("fields_mapping: unerwartete Kopfzeilen.")
        for row in r:
            oldf = (row.get(key_old) or "").strip()
            newf = (row.get(key_new) or "").strip()
            if not newf:
                continue
            field_map[oldf] = newf
            if newf not in target_order:
                target_order.append(newf)
    reverse_map = {newf: oldf for oldf, newf in field_map.items() if oldf}
    return field_map, target_order, reverse_map

def load_value_mapping(path: str) -> Dict[str, str]:
    value_map: Dict[str, str] = {}
    with open(path, encoding="utf-8", newline='') as f:
        r = csv.DictReader(f, delimiter=";")
        cols = [c.strip().lower() for c in (r.fieldnames or [])]
        if {"old_value", "new_value"}.issubset(cols):
            k_old, k_new = "old_value", "new_value"
        elif {"source_value", "treesta_value"}.issubset(cols):
            k_old, k_new = "source_value", "treesta_value"
        else:
            if r.fieldnames and len(r.fieldnames) >= 2:
                k_old, k_new = r.fieldnames[0], r.fieldnames[1]
            else:
                raise ValueError("value_mapping: unerwartete Kopfzeilen.")
        for row in r:
            oldv = (row.get(k_old) or "").strip()
            newv = (row.get(k_new) or "").strip()
            if oldv:
                value_map[oldv] = newv if newv else oldv
    return value_map

# === Wert-Mapping inkl. {…}-Logik ============================================
def map_compound_value_exact(text: str, value_map: Dict[str, str], unmapped_set: set,
                             target_key: str = "") -> str:
    if not text or not isinstance(text, str):
        return text
    if not (text.startswith("{") and text.endswith("}")):
        val = text.strip()
        if val and val not in value_map and should_track_unmapped(target_key, val):
            unmapped_set.add(val)
        return value_map.get(val, val)
    inner = text.strip("{}").strip()
    if inner in value_map:
        return "{" + value_map[inner] + "}"
    inner_clean = inner.replace(",", "")
    if inner_clean in value_map:
        return "{" + value_map[inner_clean] + "}"
    parts = re.split(r', (?=\d{2,})', inner)
    if len(parts) == 1:
        p = parts[0].strip()
        if p and p not in value_map and should_track_unmapped(target_key, p):
            unmapped_set.add(p)
        return "{" + value_map.get(p, p) + "}"
    translated = []
    for p in parts:
        s = p.strip()
        if s and s not in value_map and should_track_unmapped(target_key, s):
            unmapped_set.add(s)
        translated.append(value_map.get(s, s))
    return "{" + ", ".join(translated) + "}"

# === Kern: Konvertierung ======================================================
def convert_kataster(input_csv_path: str, field_mapping_path: str, value_mapping_path: str) -> Tuple[str, str]:
    project_dir = os.path.dirname(input_csv_path)
    out_csv = os.path.join(project_dir, "treesta_import.csv")
    unmapped_txt = os.path.join(project_dir, "unmapped_values.txt")

    field_map, target_order, reverse_field = load_field_mapping(field_mapping_path)
    value_map = load_value_mapping(value_mapping_path)

    with open(input_csv_path, encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        source_rows = list(reader)

    unmapped_values = set()
    out_rows: List[Dict[str, str]] = []

    for src in source_rows:
        dst: Dict[str, str] = {}
        aggregates: Dict[str, List[str]] = defaultdict(list)
        measures_by_urgency: Dict[str, List[str]] = defaultdict(list)

        for old_key, raw_val in src.items():
            # Mapping holen; für Koordinaten 1:1 durchlassen, auch ohne Mapping
            new_key = field_map.get(old_key, "")
            if not new_key:
                if is_coord_name(old_key):
                    new_key = old_key
                else:
                    continue

            val = (raw_val or "").strip()

            # --- BK3: measures_N + *_urgency ---------------------------------
            if (
                new_key.startswith("measures_")
                and new_key[-1].isdigit()
                and not any(suf in new_key for suf in ("_urgency", "_comment", "_date", "_name", "_time", "_costs"))
            ):
                index = new_key.split("_")[1]
                urg_old = reverse_field.get(f"measures_{index}_urgency", "")
                urg_raw = (src.get(urg_old, "") or "").strip() if urg_old else ""
                urg_mapped = map_compound_value_exact(urg_raw, value_map, unmapped_values,
                                                      target_key=f"measures_{index}_urgency") or ""
                measure_mapped = map_compound_value_exact(val, value_map, unmapped_values,
                                                          target_key=f"measures_{index}")
                measures_by_urgency[urg_mapped].append(measure_mapped)
                continue

            # --- BK4: massnahme_(hoch|normal|niedrig|sofort|optional) --------
            nk_lc = new_key.lower()
            if nk_lc.startswith(BK4_MASSNAHME_PREFIX):
                # Nur das Hauptfeld einsammeln – *_bemerkung/_datum/_name ignorieren
                if nk_lc in BK4_MASSNAHME_URGENCY:
                    urg_raw = BK4_MASSNAHME_URGENCY[nk_lc]
                    urg_mapped = map_compound_value_exact(urg_raw, value_map, unmapped_values,
                                                          target_key="measures_urgency") or urg_raw
                    measure_mapped = map_compound_value_exact(val, value_map, unmapped_values,
                                                              target_key="measures")
                    measures_by_urgency[urg_mapped].append(measure_mapped)
                    continue
                if any(suf in nk_lc for suf in ("_bemerkung", "_datum", "_name", "_comment", "_date")):
                    continue

            # Aggregierbare Ziel-Felder
            if new_key in AGGREGATE_TARGETS:
                mapped = map_compound_value_exact(val, value_map, unmapped_values, target_key=new_key)
                aggregates[new_key].append(mapped)
                continue

            # Koordinaten-Passthrough
            if is_coord_name(new_key) or is_coord_name(old_key):
                dst[new_key] = val
                continue

            # Normale Felder
            if new_key == "species":
                dst[new_key] = clean_species(val)
            else:
                original_new_key = new_key
                if new_key in ALIAS_TARGETS:
                    new_key = ALIAS_TARGETS[new_key]
                if new_key == "vitality":
                    val = re.sub(r"^\s*\d+\s*", "", val)
                mapped = map_compound_value_exact(val, value_map, unmapped_values, target_key=new_key)
                if new_key in ("condition", "vitality"):
                    prio_map = TARGET_PRIORITY[new_key]
                    incoming_prio = prio_map.get(original_new_key, 99)
                    current_prio = dst.get(f"__prio_{new_key}", 999)
                    if mapped and (incoming_prio < current_prio or not dst.get(new_key)):
                        dst[new_key] = convert_booleans(mapped)
                        dst[f"__prio_{new_key}"] = incoming_prio
                else:
                    if new_key not in dst or not dst[new_key]:
                        dst[new_key] = convert_booleans(mapped)

        # Aggregierte Felder in {…}
        for k, arr in aggregates.items():
            br = to_braced(arr)
            if br:
                dst[k] = br

        # Maßnahmen sortiert/verdichtet
        urgency_order = {
            "high": 0,          # umfasst hoch + sofort (gemappt)
            "normal": 1, "medium": 1, "mittel": 1,
            "low": 2, "niedrig": 2,
            "optional": 3,
            "": 4,
        }
        items = sorted(measures_by_urgency.items(), key=lambda kv: urgency_order.get(kv[0], 9))
        normalized = [(urg, to_braced(mlist)) for urg, mlist in items if to_braced(mlist)]

        # evtl. zuvor gesetzte Felder entfernen
        for i in range(1, 6):
            dst.pop(f"measures_{i}", None)
            dst.pop(f"measures_{i}_urgency", None)

        # kompakt ab 1 schreiben
        slot = 1
        for urg, braced in normalized:
            if slot > 5:
                break
            dst[f"measures_{slot}"] = braced
            dst[f"measures_{slot}_urgency"] = urg
            slot += 1

        # Species-Fallback
        if "species" not in dst:
            for alt in ("baumart", "art", "species"):
                if alt in src and src[alt]:
                    dst["species"] = clean_species(src[alt])
                    break

        dst.pop("__prio_condition", None)
        dst.pop("__prio_vitality", None)
        out_rows.append(dst)

    # Unmapped schreiben
    if unmapped_values:
        with open(unmapped_txt, "w", encoding="utf-8") as f:
            f.write("Nicht gemappte Werte (value_mapping ergänzen):\n")
            for v in sorted(unmapped_values):
                f.write(v + "\n")

    # Kopfzeilen
    def add_unique(lst, items):
        seen = set(lst)
        for it in items:
            if it not in seen:
                lst.append(it)
                seen.add(it)
        return lst

    present_keys, seen_keys = [], set()
    for r in out_rows:
        for k in r.keys():
            if k not in seen_keys:
                present_keys.append(k)
                seen_keys.add(k)

    headers = [k for k in target_order if k in seen_keys]

    # Generierte Felder: measures_N / measures_N_urgency – urgency immer mitnehmen
    generated_priority = []
    for i in range(1, 6):
        if f"measures_{i}" in seen_keys:
            generated_priority.append(f"measures_{i}")
            generated_priority.append(f"measures_{i}_urgency")
    headers = add_unique(headers, generated_priority)

    # Restliche vorhandene Keys alphabetisch
    residual = sorted([k for k in present_keys if k not in headers])
    headers = add_unique(headers, residual)

    with open(out_csv, "w", encoding="utf-8", newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in headers})

    return out_csv, unmapped_txt

# === Auto-Erkennung & Smart-Convert ==========================================
def detect_profile(input_csv_path: str) -> str:
    markers_bk3_prefix = ("Kontrollen_",)
    markers_bk3_exact = {
        "Kontrollen_zustand", "Kontrollen_vitalitaet",
        "Kontrollen_massnahme1", "Kontrollen_dringlichkeit1",
        "Kontrollen_massnahme2", "Kontrollen_dringlichkeit2",
    }
    with open(input_csv_path, encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter=";", quotechar='"')
        headers = next(r, [])
    headers_norm = [h.strip() for h in headers]
    if any(h.startswith(markers_bk3_prefix) for h in headers_norm) or any(h in markers_bk3_exact for h in headers_norm):
        return "baumkataster_3"
    return "baumkataster_4"

def smart_convert(input_csv_path: str, mappings_dir: str) -> Tuple[str, str, str]:
    profile = detect_profile(input_csv_path)
    fields_map = os.path.join(mappings_dir, f"fields_mapping_{profile}.csv")
    value_map  = os.path.join(mappings_dir, f"value_mapping_{profile}.csv")
    out_csv, unmapped = convert_kataster(input_csv_path, fields_map, value_map)
    return out_csv, unmapped, profile

# === CLI ======================================================================
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="BK3/BK4 → Treesta Konverter (Auto-Erkennung)")
    ap.add_argument("input_csv", help="Pfad zu export.csv")
    ap.add_argument("--fields_mapping_csv", default=None)
    ap.add_argument("--value_mapping_csv", default=None)
    ap.add_argument("--mappings_dir", default=".")
    args = ap.parse_args()

    if args.fields_mapping_csv and args.value_mapping_csv:
        out_csv, unmapped = convert_kataster(args.input_csv, args.fields_mapping_csv, args.value_mapping_csv)
        print("OK:", out_csv)
        if os.path.exists(unmapped):
            print("Hinweise:", unmapped)
    else:
        out_csv, unmapped, profile = smart_convert(args.input_csv, args.mappings_dir)
        print(f"OK ({profile}):", out_csv)
        if os.path.exists(unmapped):
            print("Hinweise:", unmapped)
