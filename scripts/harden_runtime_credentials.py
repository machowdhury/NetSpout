#!/usr/bin/env python3
"""Remove the historical disposable credential from active packaged runtime files."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = "00000000-0000-0000-0000-000000000000"

REPLACEMENTS = {
    "splunkHECToken: " + LEGACY: 'splunkHECToken: ""',
    'cfg.hec_token || "' + LEGACY + '"': 'cfg.hec_token || ""',
    'stored_cfg.get("hec_token", "' + LEGACY + '")': 'stored_cfg.get("hec_token", "")',
    'return "' + LEGACY + '";': 'return "";',
    'placeholder: "' + LEGACY + '"': 'placeholder: "Enter HEC token"',
}


def main() -> int:
    roots = [
        ROOT / "netspout" / "appserver" / "static" / "scenarios",
        ROOT / "netspout" / "appserver" / "static",
    ]
    changed = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".js", ".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            updated = text
            for old, new in REPLACEMENTS.items():
                updated = updated.replace(old, new)
            if updated != text:
                path.write_text(updated, encoding="utf-8")
                changed.append(str(path.relative_to(ROOT)))
    print(f"Hardened {len(changed)} active runtime files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
