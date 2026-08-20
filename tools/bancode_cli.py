#!/usr/bin/env python3
"""bancode_cli.py - BANcode Framework management CLI.

Usage:
    bancode build          Parse sources, generate bindings, compile libbancode.a
    bancode lookup <code>  Look up a code by hex value or name
    bancode validate       Validate all source files
    bancode stats          Show assigned vs unassigned counts
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REGISTRY = DATA_DIR / "master_registry.json"
BUILD_DIR = ROOT / "build"

SOURCE_FILES = {
    "bancode": ROOT / "bancode.txt",
    "warncode": ROOT / "warncode.txt",
    "comcode": ROOT / "comcode.txt",
    "softcode": ROOT / "softcode.txt",
}


def cmd_build(args):
    """Run full pipeline: parse -> generate -> cmake build."""
    scripts = ROOT / "scripts"

    print("[1/3] Parsing sources...")
    r = subprocess.run(
        [sys.executable, str(scripts / "parse_sources.py")],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print("Parse failed.", file=sys.stderr)
        return 1

    print("[2/3] Generating bindings...")
    r = subprocess.run(
        [sys.executable, str(scripts / "generate_bindings.py")],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print("Generation failed.", file=sys.stderr)
        return 1

    print("[3/3] Building libbancode.a...")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    r = subprocess.run(
        ["cmake", "-S", str(ROOT), "-B", str(BUILD_DIR)],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print("CMake configure failed.", file=sys.stderr)
        return 1

    r = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR)],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print("Build failed.", file=sys.stderr)
        return 1

    print("Build complete: build/lib/libbancode.a")
    return 0


def cmd_lookup(args):
    """Look up a code by hex value or name."""
    if not REGISTRY.exists():
        print("Registry not found. Run: bancode build", file=sys.stderr)
        return 1

    with open(REGISTRY, "r", encoding="utf-8") as f:
        registry = json.load(f)

    target = args.target.strip()

    # Try hex lookup
    if target.startswith("0x") or target.startswith("0X"):
        try:
            val = int(target, 16)
        except ValueError:
            print(f"Invalid hex: {target}", file=sys.stderr)
            return 1
        for slot in registry["slots"]:
            if slot["value"] == val and slot["assigned"]:
                _print_slot(slot)
                return 0
        print(f"No assigned code at 0x{val:08X}")
        return 1

    # Try name lookup (case-insensitive)
    target_upper = target.upper()
    for slot in registry["slots"]:
        if slot["name"].upper() == target_upper and slot["assigned"]:
            _print_slot(slot)
            return 0

    # Partial match
    matches = [s for s in registry["slots"]
               if target_upper in s["name"].upper() and s["assigned"]]
    if matches:
        for m in matches:
            _print_slot(m)
        return 0

    print(f"Code not found: {target}")
    return 1


def _print_slot(slot):
    status = "ASSIGNED" if slot["assigned"] else "UNASSIGNED"
    print(f"  {slot['hex']}  {slot['name']}")
    if slot["description"]:
        print(f"           {slot['description']}")
    print(f"           Category: {slot['category']}  Subcategory: {slot['subcategory']}  Status: {status}")
    print()


def cmd_validate(args):
    """Validate all source files for syntax, bounds, and collisions."""
    import re

    slot_re = re.compile(
        r"^SLOT\s+([0-9A-Fa-f]{8})\s+(\S+)(?:\s+(.+))?$"
    )

    all_slots = []
    errors = []

    for cat, path in [
        ("bancode", ROOT / "bancode.txt"),
        ("warncode", ROOT / "warncode.txt"),
        ("comcode", ROOT / "comcode.txt"),
        ("softcode", ROOT / "softcode.txt"),
    ]:
        if not path.exists():
            errors.append(f"Missing: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find block range from header
        block_start = None
        block_end = None
        for line in lines:
            m = re.match(r"^#\s+BLOCK\s+([0-9A-Fa-f]{8})-([0-9A-Fa-f]{8})", line)
            if m:
                block_start = int(m.group(1), 16)
                block_end = int(m.group(2), 16)
                break

        if block_start is None:
            errors.append(f"{cat}: no BLOCK range found in header")
            continue

        slot_count = 0
        for i, line in enumerate(lines, 1):
            line = line.rstrip("\n\r")
            m = slot_re.match(line)
            if m:
                hex_val = int(m.group(1), 16)
                name = m.group(2)
                slot_count += 1

                if hex_val < block_start or hex_val > block_end:
                    errors.append(f"{cat}:{i} hex 0x{hex_val:08X} outside block range 0x{block_start:08X}-0x{block_end:08X}")

                all_slots.append({
                    "category": cat,
                    "hex": hex_val,
                    "name": name,
                    "line": i,
                })

        print(f"  {cat}: {slot_count} slots (range 0x{block_start:08X}-0x{block_end:08X})")

    # Duplicate hex check
    hex_seen = {}
    for slot in all_slots:
        h = slot["hex"]
        if h in hex_seen:
            errors.append(f"Duplicate hex 0x{h:08X}: {slot['category']}:{slot['line']} and {hex_seen[h]['category']}:{hex_seen[h]['line']}")
        else:
            hex_seen[h] = slot

    # Duplicate name check (skip RESERVED_UNMAPPED - intentional placeholders)
    # Only flag duplicates within the same category (cross-category duplicates are intentional)
    name_seen = {}
    for slot in all_slots:
        if slot["name"] == "UNASSIGNED" or slot["name"] == "RESERVED_UNMAPPED":
            continue
        n = slot["name"]
        key = (n, slot["category"])
        if key in name_seen:
            errors.append(f"Duplicate name '{n}' in {slot['category']}: line {slot['line']} and {name_seen[key]['line']}")
        else:
            name_seen[key] = slot

    print()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    else:
        print(f"VALIDATION PASSED: {len(all_slots)} slots, {len(name_seen)} unique names, 0 collisions")
        return 0


def cmd_stats(args):
    """Show assigned vs unassigned per category."""
    if not REGISTRY.exists():
        print("Registry not found. Run: bancode build", file=sys.stderr)
        return 1

    with open(REGISTRY, "r", encoding="utf-8") as f:
        registry = json.load(f)

    total_assigned = 0
    total_slots = 0

    for cat, meta in registry["categories"].items():
        cat_slots = [s for s in registry["slots"] if s["category"] == cat]
        assigned = [s for s in cat_slots if s["assigned"]]
        total = len(cat_slots)
        pct = (len(assigned) / total * 100) if total > 0 else 0
        bar_len = 40
        filled = int(pct / 100 * bar_len)
        bar = "#" * filled + "." * (bar_len - filled)

        print(f"  {cat:10s} [{bar}] {len(assigned):4d}/{total:4d} ({pct:5.1f}%)")
        total_assigned += len(assigned)
        total_slots += total

    print()
    pct = (total_assigned / total_slots * 100) if total_slots > 0 else 0
    print(f"  {'TOTAL':10s}  {total_assigned}/{total_slots} ({pct:.1f}%)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="bancode",
        description="BANcode Framework management CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Parse, generate, compile")

    lookup_p = sub.add_parser("lookup", help="Look up a code")
    lookup_p.add_argument("target", help="Hex value (0x...) or code name")

    sub.add_parser("validate", help="Validate source files")
    sub.add_parser("stats", help="Show allocation statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "build": cmd_build,
        "lookup": cmd_lookup,
        "validate": cmd_validate,
        "stats": cmd_stats,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
