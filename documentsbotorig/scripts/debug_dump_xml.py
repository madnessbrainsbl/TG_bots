#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import zipfile

def dump(docx_path, part):
    with zipfile.ZipFile(docx_path, 'r') as z:
        data = z.read(part)
    s = data.decode('utf-8', errors='ignore')
    print(f"Length: {len(s)}")
    # Show first 5 occurrences of '{' not part of jinja delimiters context
    idxs = [i for i, ch in enumerate(s) if ch == '{']
    print(f"Total '{{' count: {len(idxs)}")
    for i in idxs[:50]:
        frag = s[max(0, i-40):i+40]
        print(f"@{i}: ...{frag}...")
    # Show counts of jinja tokens
    print("'{{' count:", s.count('{{'))
    print("'}}' count:", s.count('}}'))
    print("'{%' count:", s.count('{%'))
    print("'%}' count:", s.count('%}'))
    print()
    close_idxs = [i for i in range(len(s)-1) if s[i] == '}' and s[i+1] == '}']
    for i in close_idxs[:50]:
        frag = s[max(0, i-40):i+42]
        print(f"}}}} @{i}: ...{frag}...")
    print(f"Total positions printed for '}}': {min(50, len(close_idxs))} of {len(close_idxs)}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: debug_dump_xml.py <docx_path> <part>")
        sys.exit(1)
    dump(sys.argv[1], sys.argv[2])

