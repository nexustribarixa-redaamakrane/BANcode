#!/usr/bin/env python3
"""test_parser.py - Tests for parse_sources.py and generate_bindings.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA_DIR = ROOT / "data"
REGISTRY = DATA_DIR / "master_registry.json"


class TestParseSources(unittest.TestCase):
    """Test the parser pipeline."""

    def setUp(self):
        """Run parse_sources.py before each test."""
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "parse_sources.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, f"Parser failed:\n{r.stderr}")

    def test_registry_exists(self):
        self.assertTrue(REGISTRY.exists(), "master_registry.json not created")

    def test_registry_valid_json(self):
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_all_categories_present(self):
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        for cat in ["bancode", "warncode", "comcode", "softcode"]:
            self.assertIn(cat, data["categories"], f"Missing category: {cat}")

    def test_slot_counts(self):
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        expected = {"bancode": 2048, "warncode": 1024, "comcode": 512, "softcode": 256}
        for cat, exp_count in expected.items():
            cat_slots = [s for s in data["slots"] if s["category"] == cat]
            self.assertEqual(len(cat_slots), exp_count,
                             f"{cat}: expected {exp_count} slots, got {len(cat_slots)}")

    def test_assigned_codes_have_descriptions(self):
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        for slot in data["slots"]:
            if slot["assigned"]:
                self.assertTrue(slot["description"],
                                f"{slot['name']} at {slot['hex']} has no description")

    def test_no_duplicate_hex(self):
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        assigned = [s for s in data["slots"] if s["assigned"]]
        hexes = [s["hex"] for s in assigned]
        self.assertEqual(len(hexes), len(set(hexes)), "Duplicate hex values found")

    def test_no_duplicate_names(self):
        """No duplicate names within the same category.
        Cross-category duplicates are intentional (e.g. MBL_OWMKFS_* in bancode and softcode).
        RESERVED_UNMAPPED placeholders are also expected duplicates."""
        with open(REGISTRY, "r") as f:
            data = json.load(f)
        assigned = [s for s in data["slots"] if s["assigned"]
                     and s["name"] != "RESERVED_UNMAPPED"]
        # Check per-category uniqueness
        by_cat = {}
        for s in assigned:
            by_cat.setdefault(s["category"], []).append(s["name"])
        for cat, names in by_cat.items():
            self.assertEqual(len(names), len(set(names)),
                             f"Duplicate names in {cat}: {len(names)} vs {len(set(names))} unique")


class TestGenerateBindings(unittest.TestCase):
    """Test the binding generator."""

    def setUp(self):
        """Run full pipeline."""
        subprocess.run(
            [sys.executable, str(SCRIPTS / "parse_sources.py")],
            cwd=str(ROOT), capture_output=True,
        )
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "generate_bindings.py")],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, f"Generator failed:\n{r.stderr}")

    def test_c_headers_exist(self):
        for f in ["bancode.h", "bancode.c"]:
            path = ROOT / "kernel_inc" / "bancode" if f.endswith(".h") else ROOT / "kernel_src" / "bancode"
            self.assertTrue((path / f).exists(), f"Missing {f}")

    def test_c_headers_freestanding(self):
        """Verify C headers only use freestanding includes."""
        for header in (ROOT / "kernel_inc" / "bancode").glob("*.h"):
            with open(header, "r") as fh:
                content = fh.read()
            hosted = ["<stdio.h>", "<stdlib.h>", "<string.h>", "<malloc.h>"]
            for h in hosted:
                self.assertNotIn(h, content, f"{header.name} includes hosted header {h}")

    def test_c_source_no_dynamic_alloc(self):
        """Verify C source uses no malloc/free (checking code, not string literals)."""
        import re
        for src in (ROOT / "kernel_src" / "bancode").glob("*.c"):
            with open(src, "r") as fh:
                lines = fh.readlines()
            for line in lines:
                stripped = line.strip()
                # Skip string literals (inside quotes) and comments
                if stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("//"):
                    continue
                # Remove string literals for checking
                code = re.sub(r'"[^"]*"', '', stripped)
                self.assertNotRegex(code, r'\bmalloc\s*\(', f"{src.name} uses malloc")
                self.assertNotRegex(code, r'\bcalloc\s*\(', f"{src.name} uses calloc")
                self.assertNotRegex(code, r'\brealloc\s*\(', f"{src.name} uses realloc")
                self.assertNotRegex(code, r'\bfree\s*\(', f"{src.name} uses free")

    def test_rust_lib_exists(self):
        lib = ROOT / "rust_bindings" / "src" / "lib.rs"
        self.assertTrue(lib.exists(), "Rust lib.rs not generated")

    def test_rust_no_std(self):
        lib = ROOT / "rust_bindings" / "src" / "lib.rs"
        with open(lib, "r") as f:
            content = f.read()
        self.assertIn("#![no_std]", content, "Rust crate not no_std")

    def test_python_package_exists(self):
        for f in ["__init__.py", "registry.py"]:
            self.assertTrue(
                (ROOT / "python" / "bancode" / f).exists(),
                f"Missing python/bancode/{f}",
            )
        for cat in ["bancode", "warncode", "comcode", "softcode"]:
            self.assertTrue(
                (ROOT / "python" / "bancode" / f"{cat}.py").exists(),
                f"Missing python/bancode/{cat}.py",
            )

    def test_python_intenum(self):
        """Verify Python enums use IntEnum."""
        for cat in ["bancode", "warncode", "comcode", "softcode"]:
            path = ROOT / "python" / "bancode" / f"{cat}.py"
            with open(path, "r") as f:
                content = f.read()
            self.assertIn("IntEnum", content, f"{cat}.py doesn't use IntEnum")


if __name__ == "__main__":
    unittest.main(verbosity=2)
