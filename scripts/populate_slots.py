#!/usr/bin/env python3
"""populate_slots.py - Populate slot files with codenames from codenames.txt.

Reads codenames.txt and maps each codename to its appropriate slot in the
category's slot file based on subcategory ranges.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SLOT_FILES = {
    "bancode": ROOT / "bancode.txt",
    "warncode": ROOT / "warncode.txt",
    "comcode": ROOT / "comcode.txt",
    "softcode": ROOT / "softcode.txt",
}

CODENAMES_FILE = ROOT / "codenames.txt"


def parse_codenames(path):
    """Parse codenames.txt into {category: {subcategory: [names]}}"""
    categories = {}
    current_cat = None
    current_subcat = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")

            if line.startswith("# ====="):
                continue

            cm = re.match(r"^#\s+(\w+)\s+-\s+", line)
            if cm:
                current_cat = cm.group(1).lower()
                categories[current_cat] = {}
                current_subcat = None
                continue

            sm = re.match(r"^#\s+---\s+(.+?)\s+---$", line)
            if sm:
                current_subcat = sm.group(1)
                if current_subcat not in categories[current_cat]:
                    categories[current_cat][current_subcat] = []
                continue

            name = line.strip()
            if name and not name.startswith("#") and current_cat:
                if current_subcat not in categories[current_cat]:
                    categories[current_cat][current_subcat] = []
                categories[current_cat][current_subcat].append(name)

    return categories


def parse_slot_file(path):
    """Parse a slot file. Returns (header_lines, slots_list, subcategory_ranges)."""
    header_lines = []
    slots = []
    subcategory_ranges = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")

            sm = re.match(r"^#\s+([0-9A-Fa-f]{8})-([0-9A-Fa-f]{8})\s+(.+)$", line)
            if sm:
                subcategory_ranges.append({
                    "start": int(sm.group(1), 16),
                    "end": int(sm.group(2), 16),
                    "name": sm.group(3).strip(),
                })

            if line.startswith("SLOT"):
                parts = line.split()
                if len(parts) >= 3:
                    slots.append({
                        "hex": parts[1],
                        "name": parts[2],
                        "desc": " ".join(parts[3:]) if len(parts) > 3 else "",
                    })
            else:
                header_lines.append(line)

    return header_lines, slots, subcategory_ranges


def normalize_subcat_name(name):
    """Normalize subcategory names for matching between codenames.txt and slot file headers."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def find_subcategory_match(codename_subcat, slot_subcats):
    """Find the matching slot subcategory range for a codename subcategory."""
    cn_norm = normalize_subcat_name(codename_subcat)

    for sc in slot_subcats:
        sc_norm = normalize_subcat_name(sc["name"])

        if cn_norm == sc_norm:
            return sc

        if cn_norm in sc_norm or sc_norm in cn_norm:
            return sc

        cn_words = set(cn_norm.split())
        sc_words = set(sc_norm.split())
        if len(cn_words & sc_words) / max(len(cn_words | sc_words), 1) > 0.6:
            return sc

    return None


def populate_file(category, codename_data, slot_file):
    """Populate a single slot file with codenames."""
    header_lines, slots, subcategory_ranges = parse_slot_file(slot_file)

    if category not in codename_data:
        print(f"WARNING: No codenames found for category '{category}'")
        return False

    subcat_names = list(codename_data[category].keys())
    print(f"\n{category}: {len(subcat_names)} subcategories in codenames.txt")
    print(f"  Slot file has {len(subcategory_ranges)} subcategory ranges")

    mapping = {}
    for subcat_name in subcat_names:
        matched = find_subcategory_match(subcat_name, subcategory_ranges)
        if matched:
            mapping[subcat_name] = matched
            print(f"  '{subcat_name}' -> {matched['name']} [{matched['start']:08X}-{matched['end']:08X}]")
        else:
            print(f"  WARNING: No match for subcategory '{subcat_name}'")

    slot_idx = {}
    for sc in subcategory_ranges:
        slot_idx[sc["name"]] = sc["start"]

    new_slots = []
    for slot in slots:
        slot_val = int(slot["hex"], 16)

        if slot["name"] != "UNASSIGNED":
            new_slots.append(slot)
            continue

        assigned = False
        for subcat_name, sc_range in mapping.items():
            if sc_range["start"] <= slot_val <= sc_range["end"]:
                names = codename_data[category].get(subcat_name, [])
                current_idx = slot_val - sc_range["start"]
                if current_idx < len(names):
                    new_name = names[current_idx]
                    desc = f"{subcat_name} - {category.upper()} slot"
                    new_slots.append({
                        "hex": slot["hex"],
                        "name": new_name,
                        "desc": desc,
                    })
                    assigned = True
                    break

        if not assigned:
            new_slots.append(slot)

    output_lines = list(header_lines)
    for slot in new_slots:
        if slot["desc"]:
            output_lines.append(f"SLOT    {slot['hex']}   {slot['name']} {slot['desc']}")
        else:
            output_lines.append(f"SLOT    {slot['hex']}   {slot['name']}")

    slot_file.write_text("\n".join(output_lines) + "\n")
    return True


def main():
    codenames = parse_codenames(CODENAMES_FILE)
    print("Parsed codenames.txt:")
    for cat, subcats in codenames.items():
        total = sum(len(names) for names in subcats.values())
        print(f"  {cat}: {total} codenames in {len(subcats)} subcategories")

    for category, slot_file in SLOT_FILES.items():
        if not slot_file.exists():
            print(f"ERROR: Slot file not found: {slot_file}")
            continue

        print(f"\nProcessing {slot_file.name}...")
        populate_file(category, codenames, slot_file)

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
