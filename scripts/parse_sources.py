#!/usr/bin/env python3
"""parse_sources.py - Ingest bancode.txt, warncode.txt, comcode.txt, softcode.txt, codenames.txt.

Outputs:
    data/master_registry.json  - canonical machine-readable registry
    data/master_registry.csv   - flat CSV for tooling
"""

import json
import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

SOURCE_FILES = {
    "bancode": ROOT / "bancode.txt",
    "warncode": ROOT / "warncode.txt",
    "comcode": ROOT / "comcode.txt",
    "softcode": ROOT / "softcode.txt",
}

CODENAMES_FILE = ROOT / "codenames.txt"

SLOT_RE = re.compile(
    r"^SLOT\s+(?P<hex>[0-9A-Fa-f]{8})\s+(?P<name>\S+)(?:\s+(?P<desc>.+))?$"
)

HEADER_RE = re.compile(
    r"^#\s+(?P<key>BLOCK|ROLE|Subcategory)\s+(?P<val>.+)$"
)
SUBCAT_RE = re.compile(
    r"^\s+#\s+(?P<range>[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8})\s+(?P<name>.+)$"
)
VERSION_RE = re.compile(r"^#\s+\S+\s+\(.*\)\s+-\s+(?P<ver>\S+)")


def parse_code_file(path, category):
    """Parse a single code definition file. Returns (meta, slots)."""
    meta = {
        "category": category,
        "file": path.name,
        "version": "",
        "block_start": "",
        "block_end": "",
        "role": "",
        "subcategories": [],
    }
    slots = []

    with open(path, "r", encoding="utf-8") as f:
        current_subcat = None
        for line in f:
            line = line.rstrip("\n\r")

            vm = VERSION_RE.match(line)
            if vm:
                meta["version"] = vm.group("ver")

            hm = HEADER_RE.match(line)
            if hm:
                key, val = hm.group("key"), hm.group("val").strip()
                if key == "BLOCK":
                    parts = val.split("-")
                    meta["block_start"] = parts[0].strip()
                    meta["block_end"] = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                elif key == "ROLE":
                    meta["role"] = val

            sm = SUBCAT_RE.match(line)
            if sm:
                sc_range = sm.group("range")
                sc_name = sm.group("name").strip()
                sc_start, sc_end = sc_range.split("-")
                meta["subcategories"].append({
                    "name": sc_name,
                    "start": sc_start,
                    "end": sc_end,
                })
                current_subcat = sc_name

            mm = SLOT_RE.match(line)
            if mm:
                hex_val = mm.group("hex").upper()
                name = mm.group("name")
                desc = (mm.group("desc") or "").strip()
                slots.append({
                    "hex": hex_val,
                    "value": int(hex_val, 16),
                    "name": name,
                    "description": desc,
                    "category": category,
                    "subcategory": current_subcat or "",
                    "assigned": name != "UNASSIGNED",
                })

    return meta, slots


def parse_codenames(path):
    """Parse codenames.txt. Returns dict of category -> list of codename entries."""
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
                categories[current_cat] = []
                current_subcat = None
                continue

            sm = re.match(r"^#\s+---\s+(.+?)\s+---$", line)
            if sm:
                current_subcat = sm.group(1)
                continue

            name = line.strip()
            if name and not name.startswith("#") and current_cat:
                categories[current_cat].append({
                    "name": name,
                    "subcategory": current_subcat or "",
                })

    return categories


def detect_duplicates(all_slots):
    """Check for duplicate hex values and duplicate names."""
    hex_map = {}
    name_map = {}
    duplicates = []

    for slot in all_slots:
        h = slot["hex"]
        n = slot["name"]
        if h in hex_map and slot["assigned"]:
            duplicates.append({
                "type": "duplicate_hex",
                "hex": h,
                "names": [hex_map[h], n],
            })
        elif slot["assigned"]:
            hex_map[h] = n

        if n != "UNASSIGNED" and n in name_map:
            duplicates.append({
                "type": "duplicate_name",
                "name": n,
                "hexes": [name_map[n], h],
            })
        elif n != "UNASSIGNED":
            name_map[n] = h

    return duplicates


def detect_gaps(slots, meta):
    """Find unassigned slots within the block range."""
    assigned = [s for s in slots if s["assigned"]]
    total = len(slots)
    unassigned = total - len(assigned)
    return {
        "total_slots": total,
        "assigned": len(assigned),
        "unassigned": unassigned,
    }


def build_registry():
    """Main entry: parse all sources, build registry, write outputs."""
    all_meta = {}
    all_slots = []
    errors = []

    for cat, path in SOURCE_FILES.items():
        if not path.exists():
            errors.append(f"Source file not found: {path}")
            continue
        meta, slots = parse_code_file(path, cat)
        all_meta[cat] = meta
        all_slots.extend(slots)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    codenames = {}
    if CODENAMES_FILE.exists():
        codenames = parse_codenames(CODENAMES_FILE)

    duplicates = detect_duplicates(all_slots)
    if duplicates:
        print(f"WARNING: {len(duplicates)} duplicate(s) detected:", file=sys.stderr)
        for d in duplicates:
            print(f"  {d}", file=sys.stderr)

    stats = {}
    for cat, meta in all_meta.items():
        cat_slots = [s for s in all_slots if s["category"] == cat]
        stats[cat] = detect_gaps(cat_slots, meta)

    registry = {
        "version": "1.0.0",
        "categories": all_meta,
        "codenames": codenames,
        "slots": all_slots,
        "stats": stats,
        "duplicates": duplicates,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    json_path = DATA_DIR / "master_registry.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    print(f"Wrote {json_path}")

    csv_path = DATA_DIR / "master_registry.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "hex", "value", "name", "category", "subcategory",
            "description", "assigned",
        ])
        writer.writeheader()
        for slot in all_slots:
            writer.writerow({
                "hex": slot["hex"],
                "value": slot["value"],
                "name": slot["name"],
                "category": slot["category"],
                "subcategory": slot["subcategory"],
                "description": slot["description"],
                "assigned": slot["assigned"],
            })
    print(f"Wrote {csv_path}")

    for cat, st in stats.items():
        print(f"  {cat}: {st['assigned']}/{st['total_slots']} assigned ({st['unassigned']} free)")

    return 0


if __name__ == "__main__":
    sys.exit(build_registry())
