#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Locate Jinja2 TemplateSyntaxError inside DOCX templates by compiling XML parts.
Reports file, part, line number, and context.
"""
from pathlib import Path
import zipfile
from jinja2 import Environment, TemplateSyntaxError

DOCX_NAMES = ["template.docx", "template1.docx", "template11.docx"]
PARTS = [
    "word/document.xml",
    # include headers/footers
    *[f"word/header{i}.xml" for i in range(1, 8)],
    *[f"word/footer{i}.xml" for i in range(1, 8)],
]

def check_docx(docx_path: Path):
    print(f"\nChecking: {docx_path}")
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            env = Environment()
            for part in PARTS:
                if part not in z.namelist():
                    continue
                src = z.read(part).decode('utf-8', errors='ignore')
                try:
                    env.from_string(src)
                except TemplateSyntaxError as e:
                    print(f"  BAD in {part} at line {e.lineno}: {e}")
                    # Print nearby context lines
                    lines = src.splitlines()
                    start = max(0, (e.lineno or 1) - 4)
                    end = min(len(lines), (e.lineno or 1) + 3)
                    for i in range(start, end):
                        mark = '>>' if (i + 1) == e.lineno else '  '
                        print(f"  {mark} {i+1:5d}: {lines[i][:160]}")
                    return False
            print("  OK")
            return True
    except Exception as ex:
        print(f"  ERROR reading {docx_path}: {ex}")
        return False


def main():
    root = Path('templates')
    any_bad = False
    for slug_dir in sorted(root.iterdir()):
        if not slug_dir.is_dir():
            continue
        for name in DOCX_NAMES:
            p = slug_dir / name
            if p.exists():
                ok = check_docx(p)
                if not ok:
                    any_bad = True
    if any_bad:
        print("\nSummary: some templates have TemplateSyntaxError. See details above.")
    else:
        print("\nSummary: all templates compiled OK.")

if __name__ == '__main__':
    main()

