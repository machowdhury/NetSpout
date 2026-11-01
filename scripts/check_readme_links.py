#!/usr/bin/env python3
"""Fail if a relative Markdown link or <img src> in README.md (or docs/guides/12) points at a missing file. Usage: python scripts/check_readme_links.py [file ...]"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bad = 0
for name in sys.argv[1:] or ["README.md", "docs/guides/12_NETFLOW_IPFIX_SOLUTION.md"]:
    f = ROOT / name
    text = f.read_text(encoding="utf-8")
    refs = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'(?:src|href)="([^"]+)"', text)
    for ref in refs:
        if re.match(r"(https?:|mailto:|#)", ref):
            continue
        path = (f.parent / ref.split("#")[0]).resolve()
        if not path.exists():
            bad += 1
            print("MISSING", name, "->", ref)
print("checked; missing:", bad)
sys.exit(1 if bad else 0)
