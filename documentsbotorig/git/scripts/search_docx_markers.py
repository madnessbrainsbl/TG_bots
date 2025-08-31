#!/usr/bin/env python
# -*- coding: utf-8 -*-
import zipfile
import sys
from pathlib import Path

def scan(path: Path):
    with zipfile.ZipFile(path,'r') as z:
        for name in z.namelist():
            if not (name.startswith('word/') and name.endswith('.xml')):
                continue
            s=z.read(name).decode('utf-8','ignore')
            has_table = ('TABLE' in s) or ('__TABLE_' in s) or ('<<TABLE' in s)
            has_anchor = ('перечень' in s.lower())
            if has_table or has_anchor:
                print(f"{name}: TABLE={has_table} ANCHOR={has_anchor}")

if __name__=='__main__':
    for p in [
        Path('templates/add_agreement_OOO/template.docx'),
        Path('templates/add_agreement_kalnysh/template.docx'),
        Path('templates/fl_ld_avtorskiy_gorki_records/template.docx'),
    ]:
        if p.exists():
            print(f"\nScanning {p}")
            scan(p)
        else:
            print(f"Missing {p}")

