#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from docxtpl import DocxTemplate
from jinja2 import exceptions as jinja_exc

DOCX_GLOBS = [
    "templates/*/template.docx",
    "templates/*/template1.docx",
    "templates/*/template11.docx",
]

bad = []
for pattern in DOCX_GLOBS:
    for p in Path('.').glob(pattern):
        try:
            doc = DocxTemplate(str(p))
            # Trigger compilation without rendering context
            # This calls jinja compile phase internally
            try:
                _ = doc.get_undeclared_template_variables()
            except AttributeError:
                # Fallback: render with empty context should still compile; Undefineds may occur later
                doc.render({})
            print(f"OK: {p}")
        except jinja_exc.TemplateSyntaxError as e:
            print(f"BAD: {p} :: TemplateSyntaxError: {e}")
            bad.append((p, e))
        except Exception as e:
            # Any other error
            print(f"WARN: {p} :: {type(e).__name__}: {e}")

if bad:
    print("\nSummary of TemplateSyntaxError:")
    for p, e in bad:
        print(f" - {p}: {e}")

