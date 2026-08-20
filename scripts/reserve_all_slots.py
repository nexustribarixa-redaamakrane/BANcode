#!/usr/bin/env python3
"""Replace all actual code definitions with UNASSIGNED across all source files."""
import re
import sys
from pathlib import Path

SOURCE_FILES = [
    Path(__file__).parent.parent / "bancode.txt",
    Path(__file__).parent.parent / "warncode.txt",
    Path(__file__).parent.parent / "comcode.txt",
    Path(__file__).parent.parent / "softcode.txt",
]

def process_file(filepath: Path) -> None:
    lines = filepath.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("SLOT"):
            parts = line.split()
            if len(parts) >= 3 and parts[2] != "UNASSIGNED":
                new_lines.append(f"{parts[0]}    {parts[1]}   UNASSIGNED")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    filepath.write_text("\n".join(new_lines) + "\n")
    print(f"Processed {filepath.name}")

def main():
    for f in SOURCE_FILES:
        if f.exists():
            process_file(f)
    print("Done - all slots reserved")

if __name__ == "__main__":
    main()
