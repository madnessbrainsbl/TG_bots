#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-fix common Jinja2 placeholder issues inside DOCX templates.
- Repairs triple braces {{{ / }}} to {{ / }}
- Removes stray single '{' or '}' not belonging to {{ }}, {% %}
- Processes word/document.xml and all word/header*.xml, word/footer*.xml
- Creates .bak backup before writing
"""
import re
import sys
import zipfile
from pathlib import Path
import shutil
from typing import Tuple, Dict

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"

DOCX_NAMES = ["template.docx", "template1.docx", "template11.docx"]

RE_TRIPLE_OPEN = re.compile(r"\{\{\{+")
RE_TRIPLE_CLOSE = re.compile(r"\}\}\}+")
# single '{' not followed by '{' or '%' (so it's not {{ or {%)
RE_STRAY_OPEN = re.compile(r"(?<!\{)\{(?!\{|%)")
# single '}' not preceded by '}' or '%' (so it's not }} or %})
RE_STRAY_CLOSE = re.compile(r"(?<![}%])\}(?!\})")

# We also normalize curly quotes (sometimes copied from Word)
CURLY_OPEN = "{"
CURLY_CLOSE = "}"


def _balance_inner_braces(expr: str) -> Tuple[str, Dict[str, int]]:
    """Within Jinja print expression content, remove extra unmatched braces.
    Keeps balanced cases (e.g., dict literals) intact. Only removes surplus.
    """
    s = expr
    stats = {"inner_removed_open": 0, "inner_removed_close": 0}
    # Count inner braces
    open_cnt = s.count('{')
    close_cnt = s.count('}')
    if open_cnt == close_cnt:
        return s, stats
    if open_cnt > close_cnt:
        # remove (open_cnt - close_cnt) earliest '{'
        to_remove = open_cnt - close_cnt
        out_chars = []
        for ch in s:
            if ch == '{' and to_remove > 0:
                to_remove -= 1
                stats["inner_removed_open"] += 1
                continue
            out_chars.append(ch)
        s = ''.join(out_chars)
    elif close_cnt > open_cnt:
        # remove (close_cnt - open_cnt) latest '}'
        to_remove = close_cnt - open_cnt
        out_chars = []
        for ch in reversed(s):
            if ch == '}' and to_remove > 0:
                to_remove -= 1
                stats["inner_removed_close"] += 1
                continue
            out_chars.append(ch)
        s = ''.join(reversed(out_chars))
    return s, stats


def fix_xml(xml: str) -> tuple[str, dict]:
    """Return fixed XML and stats of fixes applied."""
    stats = {
        "triple_open": 0,
        "triple_close": 0,
        "stray_open": 0,
        "stray_close": 0,
        "inner_removed_open": 0,
        "inner_removed_close": 0,
        "before_open": xml.count("{{"),
        "before_close": xml.count("}}"),
    }
    out = xml

    # Fix triple/more braces first
    def _sub_count(pat: re.Pattern, repl: str, s: str, key: str):
        def _repl(m):
            stats[key] += 1
            return repl
        return pat.sub(_repl, s)

    out = _sub_count(RE_TRIPLE_OPEN, "{{", out, "triple_open")
    out = _sub_count(RE_TRIPLE_CLOSE, "}}", out, "triple_close")

    # Remove stray single braces
    out, c_open = RE_STRAY_OPEN.subn("", out)
    stats["stray_open"] += c_open
    out, c_close = RE_STRAY_CLOSE.subn("", out)
    stats["stray_close"] += c_close

    # Balance inner braces only inside {{ ... }} expressions
    def _balance_in_prints(text: str) -> Tuple[str, int, int]:
        removed_open_total = 0
        removed_close_total = 0
        def repl(m):
            nonlocal removed_open_total, removed_close_total
            inner = m.group(1)
            fixed, sstats = _balance_inner_braces(inner)
            removed_open_total += sstats["inner_removed_open"]
            removed_close_total += sstats["inner_removed_close"]
            return "{{" + fixed + "}}"
        new_text = re.sub(r"\{\{(.*?)\}\}", repl, text, flags=re.DOTALL)
        return new_text, removed_open_total, removed_close_total

    out, ro, rc = _balance_in_prints(out)
    stats["inner_removed_open"] += ro
    stats["inner_removed_close"] += rc

    # Add missing closing '}}' before </w:t> for unclosed variables like '{{ passport'
    def _close_unclosed_vars(text: str) -> Tuple[str, int]:
        added = 0
        pattern = re.compile(r"(\{\{[^<>]*?)(</w:t>)")
        def repl(m):
            nonlocal added
            prefix = m.group(1)
            if '}}' in prefix:
                return m.group(0)
            # add a space before closing for readability inside XML text
            added += 1
            return prefix.rstrip() + ' }}' + m.group(2)
        new_text = pattern.sub(repl, text)
        return new_text, added

    out, added_closers = _close_unclosed_vars(out)
    if added_closers:
        stats["added_missing_closers"] = added_closers

    # Remove empty prints like '{{ }}' which cause 'Expected an expression, got end of print statement'
    empty_before = out.count('{{ }}')
    out = out.replace('{{ }}', '')
    if empty_before:
        stats["removed_empty_prints"] = empty_before

    # Fix closers without opener within same <w:t> by inserting missing '{{ var '
    def _add_missing_openers(text: str) -> Tuple[str, int]:
        added = 0
        # We limit to current <w:t> to avoid spanning across XML tags
        pat = re.compile(r"(<w:t[^>]*>)([^<{}]{0,80}?)([A-Za-z_][A-Za-z0-9_]*)\s*}}(\s*)(</w:t>)")
        def repl(m):
            nonlocal added
            start, pre, var, space, end = m.groups()
            if '{{' in pre:
                return m.group(0)
            added += 1
            pre_fixed = pre.rstrip()
            # Insert '{{ var }}' respecting spacing
            return f"{start}{pre_fixed} {{ {{ {var} }} }}{space}{end}"
        new_text = pat.sub(repl, text)
        return new_text, added

    out, added_openers = _add_missing_openers(out)
    if added_openers:
        stats["added_missing_openers"] = added_openers

    stats["after_open"] = out.count("{{")
    stats["after_close"] = out.count("}}")

    return out, stats


def patch_docx(docx_path: Path) -> dict:
    """Patch word/*.xml inside docx and write changes; returns summary stats."""
    changed = False
    summary = {"file": str(docx_path), "parts": []}

    tmp_path = docx_path.with_suffix(".tmp")
    bak_path = docx_path.with_suffix(".bak")

    with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.endswith('.xml') and info.filename.startswith('word/') and not info.filename.endswith('.rels'):
                try:
                    xml = data.decode('utf-8')
                except UnicodeDecodeError:
                    # fallback if needed
                    xml = data.decode('utf-8', errors='ignore')
                fixed, stats = fix_xml(xml)
                if fixed != xml:
                    changed = True
                    summary["parts"].append({
                        "part": info.filename,
                        **stats,
                    })
                    data = fixed.encode('utf-8')
            zout.writestr(info, data)

    if changed:
        if not bak_path.exists():
            shutil.copy2(docx_path, bak_path)
        # Replace original
        tmp_path.replace(docx_path)
    else:
        tmp_path.unlink(missing_ok=True)

    summary["changed"] = changed
    return summary


def main():
    if not TEMPLATES_DIR.exists():
        print(f"❌ Templates dir not found: {TEMPLATES_DIR}")
        sys.exit(1)

    docx_files = []
    for slug_dir in TEMPLATES_DIR.iterdir():
        if slug_dir.is_dir():
            for name in DOCX_NAMES:
                p = slug_dir / name
                if p.exists():
                    docx_files.append(p)

    if not docx_files:
        print("⚠️ No template .docx files found")
        return

    any_changed = False
    for f in docx_files:
        res = patch_docx(f)
        if res["changed"]:
            any_changed = True
            print(f"✔ Fixed: {res['file']}")
            for part in res["parts"]:
                print(f"  - {part['part']}: triple_open={part['triple_open']} triple_close={part['triple_close']} stray_open={part['stray_open']} stray_close={part['stray_close']} ({{ before={part['before_open']}; }} before={part['before_close']} -> {{ after={part['after_open']}; }} after={part['after_close']})")
        else:
            print(f"OK: {res['file']} (no changes)")

    if any_changed:
        print("\n✅ Changes applied. Backups saved as .bak next to originals.")
    else:
        print("\nℹ️ Nothing to fix.")


if __name__ == "__main__":
    main()

