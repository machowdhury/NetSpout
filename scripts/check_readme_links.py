#!/usr/bin/env python3
"""Fail if a relative Markdown link, <img src>, #anchor or backticked repo path (scripts/, docs/, deploy/, tests/, src/, backend/) in the given Markdown files points at something missing. Usage: python scripts/check_readme_links.py [file ...]"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bad = 0
def slugs(text):
    out = set()
    for h in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.M):
        out.add(re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", re.sub(r"[`*]", "", h).lower())))
    return out


DEFAULT = ["README.md", "docs/QUICKSTART.md"] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs/guides").glob("*.md"))
for name in sys.argv[1:] or DEFAULT:
    f = ROOT / name
    text = f.read_text(encoding="utf-8")
    refs = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'(?:src|href)="([^"]+)"', text)
    refs = [r for r in refs if not r.startswith("<")]
    for ref in refs:
        if re.match(r"(https?:|mailto:|#)", ref):
            continue
        path = (f.parent / ref.split("#")[0]).resolve() if ref.split("#")[0] else f
        if not path.exists():
            bad += 1
            print("MISSING", name, "->", ref)
        elif "#" in ref and path.suffix == ".md" and ref.split("#")[1] not in slugs(path.read_text(encoding="utf-8")):
            bad += 1
            print("BAD ANCHOR", name, "->", ref)
    for ref in set(re.findall(r"`((?:scripts|docs|deploy|tests|src|backend)/[\w./-]+\.\w+)`", text)):
        if not (ROOT / ref).exists():
            bad += 1
            print("MISSING PATH", name, "->", ref)
print("checked; missing:", bad)
sys.exit(1 if bad else 0)
